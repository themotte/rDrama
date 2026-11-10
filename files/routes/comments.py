from sqlalchemy import text
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import set_committed_value

from files.__main__ import app, limiter
from files.classes import *
from files.classes.visstate import StateMod
from files.helpers.alerts import *
from files.helpers.comments import comment_counted, comment_on_publish, comment_published, comment_sort, comment_state_change, update_author_comment_count
from files.helpers.config.const import *
from files.helpers.locks import user_shadowbanned_locked
from files.helpers.media import attach_images
from files.helpers.notifications import load_messages, mark_threads_read
from files.helpers.wrappers import *
from files.routes.importstar import *

from datetime import datetime, timezone

# Collect just the comment ids the context view actually renders: the focused
# comment's subtree (down to the render depth limit, +1 level so the boundary
# "more comments" button still appears) and its ancestor chain (up `context`
# levels, +1 so top_comment.parent_comment stays wired). This replaces loading
# the entire top-comment thread and discarding most of it. Both keep to the
# focused comment's post: older versions let private replies hang under
# comments on posts.
_CONTEXT_COMMENT_IDS_SQL = text("""
WITH RECURSIVE focus AS (
		SELECT parent_submission FROM comments WHERE id = :cid
), subtree(id, depth) AS (
		SELECT id, 0 FROM comments WHERE id = :cid
	UNION ALL
		SELECT c.id, s.depth + 1
		FROM comments c JOIN subtree s ON c.parent_comment_id = s.id
		WHERE s.depth < :subtree_depth AND c.parent_submission IS NOT DISTINCT FROM (SELECT parent_submission FROM focus)
), ancestors(id, parent_comment_id, depth) AS (
		SELECT id, parent_comment_id, 0 FROM comments WHERE id = :cid
	UNION ALL
		SELECT c.id, c.parent_comment_id, a.depth + 1
		FROM comments c JOIN ancestors a ON c.id = a.parent_comment_id
		WHERE a.depth < :ancestor_depth AND c.parent_submission IS NOT DISTINCT FROM (SELECT parent_submission FROM focus)
)
SELECT id FROM subtree
UNION
SELECT id FROM ancestors
""")

@app.get("/comment/<id:cid>")
@app.get("/post/<id:pid>/<anything>/<id:cid>")
@auth_desired
def post_pid_comment_cid(cid, pid=None, anything=None, v=None):
	comment = g.db.get(Comment, cid)
	if not comment: abort(404)

	if not comment.parent_submission:
		if pid: abort(404)
		return _message_page(comment, v)

	if not pid: pid = comment.parent_submission

	post = get_post(pid, v=v)

	if comment.parent_submission and comment.parent_submission != post.id: abort(404)
	if post.is_draft_hidden_from(v): abort(404)

	if age_unconfirmed(post, v):
		if request.headers.get("Authorization") or request.headers.get("xhr"): abort(403, "Must be 18+ to view")
		return render_template("errors/nsfw.html", v=v)

	sort = comment_sort(request.values.get("sort"), v)

	try: context = max(0, min(int(request.values.get("context", 0)), 8))
	except: context = 0

	# Load only the comments we render, not the whole top-comment thread.
	context_ids = [row[0] for row in g.db.execute(_CONTEXT_COMMENT_IDS_SQL, {
		"cid": comment.id,
		"subtree_depth": RENDER_DEPTH_LIMIT,
		"ancestor_depth": context + 1,
	})]

	def comment_tree_filter(q):
		return q.filter(Comment.id.in_(context_ids))

	comments, comment_tree = get_comment_trees_eager(comment_tree_filter, sort=sort, v=v, post=post)
	set_committed_value(post, 'comments', comments)

	comment_info = comment
	c = comment
	while context and c.level > 1 and c.parent_comment.is_open_to(v):
		c.parent_comment.replies2 = [c]
		c = c.parent_comment
		context -= 1
	top_comment = c

	post.replies=[top_comment]
			
	if request.headers.get("Authorization"): page = top_comment.json_for(v)
	else: page = render_template("submission.html", v=v, p=post, sort=sort, comment_info=comment_info, render_replies=True)

	_mark_read(comment, v)
	return page


def _mark_read(comment:Comment, v:Optional[User]):
	'''Marks `v`'s notification of `comment` read, when the request asks to ("read").'''
	if v and request.values.get("read"):
		g.db.query(Notification).filter_by(comment_id=comment.id, user_id=v.id, read=False).update({Notification.read: True})
		g.db.commit()


def _message_page(message:Comment, v:Optional[User]):
	'''A message's conversation from the message down, at any depth, with "context" messages above it.'''
	if not message.is_open_to(v): abort(403)

	try: context = max(0, min(int(request.values.get("context", 0)), 8))
	except ValueError: context = 0

	# Its conversation's messages; a notice, or a message older versions left outside any conversation, stands alone
	top = message.thread_top
	loaded = load_messages(Comment.top_comment_id == top.id if top else Comment.id == message.id, v)
	focus = loaded[message.id]
	c = focus
	while context and c.parent_comment_id in loaded and c.parent_comment.is_open_to(v):
		c.parent_comment.replies2 = [c]
		c = c.parent_comment
		context -= 1

	mark_threads_read([c], v)
	if request.headers.get("Authorization"): page = c.json_for(v)
	else: page = render_template("conversation.html", v=v, top_comment=c, comment_info=focus)
	g.db.commit()
	return page

@app.post("/comment")
@limiter.limit("1/second;20/minute;200/hour;1000/day")
@auth_required
def api_comment(v):
	if v.is_suspended: abort(403, "You can't perform this action while banned.")

	parent_fullname = request.values.get("parent_fullname", "").strip()

	if len(parent_fullname) < 4: abort(400)
	parent = None
	parent_post = None
	parent_comment_id = None

	if parent_fullname.startswith("post_"):
		parent = get_post(parent_fullname.split("post_")[1], v=v)
		parent_post = parent
	elif parent_fullname.startswith("comment_"):
		parent = get_comment(parent_fullname.split("comment_")[1], v=v)
		parent_post = get_post(parent.parent_submission, v=v) if parent.parent_submission else None
		parent_comment_id = parent.id
	else: abort(400)
	if not parent_post or parent_post.is_draft_hidden_from(v): abort(404)
	level = 1 if isinstance(parent, Submission) else parent.level + 1

	body = sanitize_raw(request.values.get("body"), allow_newlines=True, length_limit=COMMENT_BODY_LENGTH_MAXIMUM)
	_, body = attach_images(body, request.files.getlist('file'))

	if not body: abort(400, "You need to actually write something!")
	if len(body) > COMMENT_BODY_LENGTH_MAXIMUM: abort(400, f"Maximum length for a comment is {COMMENT_BODY_LENGTH_MAXIMUM}, including the links to attached images")

	body_html = sanitize(body)

	existing = g.db.query(Comment.id).filter(
		Comment.author_id == v.id,
		Comment.state_user_deleted_utc == None,
		Comment.parent_comment_id == parent_comment_id,
		Comment.parent_submission == parent_post.id,
		Comment.body_html == body_html
	).first()

	if existing:
		abort(409, f"You already made that comment: /comment/{existing.id}")

	replying_to_blocked = parent.author.is_blocking(v) and v.admin_level < 2

	is_bot = bool(request.headers.get("Authorization"))

	if not is_bot and len(body) > 10:
		now = int(time.time())
		cutoff = now - 60 * 60 * 24

		similar_comments = g.db.query(Comment).filter(
			Comment.author_id == v.id,
			Comment.body.op(
				'<->')(body) < app.config["COMMENT_SPAM_SIMILAR_THRESHOLD"],
			Comment.created_utc > cutoff
		).count()

		threshold = app.config["COMMENT_SPAM_COUNT_THRESHOLD"]
		if v.age_seconds >= (60 * 60 * 24 * 7):
			threshold *= 3
		elif v.age_seconds >= (60 * 60 * 24):
			threshold *= 2

		if similar_comments > threshold:
			abort(403, "Too much spam!")

	is_filtered = v.should_comments_be_filtered

	if (v.admin_level <= PERMS['POST_COMMENT_MODERATION'] 
		and len(body) > COMMENT_BODY_LENGTH_MAXIMUM_UNFILTERED):
		is_filtered = True

	c = Comment(author_id=v.id,
				parent_submission=parent_post.id,
				parent_comment_id=parent_comment_id,
				level=level,
				over_18=parent_post.over_18 or request.values.get("over_18")=="true",
				is_bot=is_bot,
				app_id=v.client.application.id if v.client else None,
				body_html=body_html,
				body=body,
				ghost=parent_post.ghost,
				state_mod=StateMod.FILTERED if is_filtered else StateMod.VISIBLE,
				)

	# The author's own upvote counts unless they're shadowbanned
	shadowbanned = user_shadowbanned_locked(g.db, v)
	c.upvotes = c.realupvotes = 0 if shadowbanned else 1
	g.db.add(c)
	g.db.flush()

	if c.level == 1: c.top_comment_id = c.id
	else: c.top_comment_id = parent.top_comment_id

	if comment_counted(c):
		comment_on_publish(c)
	update_author_comment_count(c)

	vote = CommentVote(user_id=v.id,
						 comment_id=c.id,
						 vote_type=1,
						 real=not shadowbanned,
						 )
	g.db.add(vote)

	c.voted = 1

	g.db.commit()

	if request.headers.get("Authorization"): return c.json_for(v)

	# Re-fetch with eager-loaded relationships so the comment template
	# (author popover, reports) doesn't lazy-load per-field.
	c = g.db.query(Comment).filter_by(id=c.id).options(
		selectinload(Comment.author).options(*author_load_options(v)),
		selectinload(Comment.post),
		selectinload(Comment.reports).options(
			selectinload(CommentFlag.user),
		),
		selectinload(Comment.senttouser),
	).one()
	c.voted = 1

	if replying_to_blocked:
		message = "This user has blocked you. You are still welcome to reply " \
				  "but you will be held to a higher standard of civility than you would be otherwise"
	elif (v.admin_level <= PERMS['POST_COMMENT_MODERATION']
			and len(body) > COMMENT_BODY_LENGTH_MAXIMUM_UNFILTERED):
		message = "Your comment has been submitted but is a bit long, so it's pending approval."
	else:
		message = None
	return {"comment": render_template("comments.html", v=v, comments=[c], ajax=True, parent_level=level), "message": message}

@app.post("/edit_comment/<id:cid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def edit_comment(cid, v):
	refuse_while_suspended(v)
	c = get_comment(cid, v=v)
	if c.author_id != v.id: abort(403)
	length_limit = MESSAGE_BODY_LENGTH_MAXIMUM if c.is_message else COMMENT_BODY_LENGTH_MAXIMUM
	body = sanitize_raw(request.values.get("body"), allow_newlines=True, length_limit=length_limit)

	uploading = any(request.files.getlist('file'))
	if uploading and c.is_message and not (c.thread_top and c.thread_top.sentto == MODMAIL_ID): abort(400, "Images can only be attached in modmail.")
	if len(body) < 1 and not uploading:
		abort(400, "You have to actually type something!")

	if body != c.body or uploading:
		body_html = sanitize(body)

		# Spam Checking
		now = int(time.time())
		cutoff = now - 60 * 60 * 24

		similar_comments = g.db.query(Comment
		).filter(
			Comment.author_id == v.id,
			Comment.body.op(
				'<->')(body) < app.config["SPAM_SIMILARITY_THRESHOLD"],
			Comment.created_utc > cutoff
		).count()

		threshold = app.config["SPAM_SIMILAR_COUNT_THRESHOLD"]
		if v.age_seconds >= (60 * 60 * 24 * 30):
			threshold *= 4
		elif v.age_seconds >= (60 * 60 * 24 * 7):
			threshold *= 3
		elif v.age_seconds >= (60 * 60 * 24):
			threshold *= 2

		if similar_comments > threshold:
			abort(403, "Too much spam!")
		# End Spam Checking

		attached, body = attach_images(body, request.files.getlist('file'))
		if attached:
			if len(body) > length_limit: abort(400, f"Maximum length is {length_limit}, including the links to attached images")
			body_html = sanitize(body)

		made_long = len(c.body or "") <= COMMENT_BODY_LENGTH_MAXIMUM_UNFILTERED < len(body)
		c.body = body
		c.body_html = body_html

		if int(time.time()) - c.created_utc > 60 * 3: c.edited_utc = int(time.time())

		if made_long and c.state_mod == StateMod.VISIBLE and v.admin_level <= PERMS['POST_COMMENT_MODERATION']:
			with comment_state_change(c):
				c.state_mod = StateMod.FILTERED

		g.db.add(c)
		
		if comment_published(c):
			notify_users = NOTIFY_USERS(body, v)

			for x in notify_users:
				notif = g.db.query(Notification) \
					.filter_by(comment_id=c.id, user_id=x).one_or_none()
				if not notif:
					n = Notification(comment_id=c.id, user_id=x)
					g.db.add(n)

		g.db.commit()

	return {"comment": c.realbody(v)}


@app.post("/delete/comment/<id:cid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def delete_comment(cid, v):
	c = get_comment(cid, v=v)
	if c.author_id != v.id: abort(403)
	if c.state_user_deleted_utc: abort(409)
	with comment_state_change(c):
		c.state_user_deleted_utc = datetime.now(tz=timezone.utc)
	g.db.add(c)
	g.db.commit()

	return {"message": "Comment deleted!"}

@app.post("/undelete/comment/<id:cid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def undelete_comment(cid, v):
	refuse_while_suspended(v)
	c = get_comment(cid, v=v)
	if c.author_id != v.id: abort(403)
	if not c.state_user_deleted_utc: abort(409)
	with comment_state_change(c):
		c.state_user_deleted_utc = None
	g.db.add(c)
	g.db.commit()

	return {"message": "Comment undeleted!"}


def _saveable(comment, v):
	'''Only comments on posts the viewer can see can be saved.'''
	return bool(comment.parent_submission) and comment.is_open_to(v)


@app.post("/save_comment/<id:cid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def save_comment(cid, v):
	comment=get_comment(cid)
	if not _saveable(comment, v): abort(404)

	save=g.db.query(CommentSaveRelationship).filter_by(user_id=v.id, comment_id=comment.id).one_or_none()

	if not save:
		new_save=CommentSaveRelationship(user_id=v.id, comment_id=comment.id)
		g.db.add(new_save)

		g.db.commit()

	return {"message": "Comment saved!"}

@app.post("/unsave_comment/<id:cid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def unsave_comment(cid, v):
	comment=get_comment(cid)

	save=g.db.query(CommentSaveRelationship).filter_by(user_id=v.id, comment_id=comment.id).one_or_none()

	if save:
		g.db.delete(save)
		g.db.commit()
	elif not _saveable(comment, v): abort(404)

	return {"message": "Comment unsaved!"}
