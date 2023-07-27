from files.__main__ import app, limiter
from files.classes import *
from files.classes.visstate import StateMod
from files.helpers.alerts import *
from files.helpers.comments import comment_on_publish
from files.helpers.config.const import *
from files.helpers.media import process_image
from files.helpers.wrappers import *
from files.routes.importstar import *

from datetime import datetime, timezone

@app.get("/comment/<cid>")
@app.get("/post/<pid>/<anything>/<cid>")
@auth_desired
def post_pid_comment_cid(cid, pid=None, anything=None, v=None):
	comment = get_comment(cid, v=v)

	if v and request.values.get("read"):
		notif = g.db.query(Notification).filter_by(comment_id=cid, user_id=v.id, read=False).one_or_none()
		if notif:
			notif.read = True
			g.db.add(notif)
			g.db.commit()

	if comment.post and comment.post.club and not (v and (v.paid_dues or v.id in [comment.author_id, comment.post.author_id])): abort(403)

	if comment.post and comment.post.private and not (v and (v.admin_level >= 2 or v.id == comment.post.author.id)): abort(403)

	if not comment.parent_submission and not (v and (comment.author.id == v.id or comment.sentto == v.id)) and not (v and v.admin_level >= 2) : abort(403)
	
	if not pid:
		if comment.parent_submission: pid = comment.parent_submission
		else: pid = 1

	post = get_post(pid, v=v)
	
	if post.over_18 and not (v and v.over_18) and not session.get('over_18', 0) >= int(time.time()):
		if request.headers.get("Authorization"): return {'error': 'This content is not suitable for some users and situations.'}
		else: return render_template("errors/nsfw.html", v=v)

	try: context = min(int(request.values.get("context", 0)), 8)
	except: context = 0
	comment_info = comment
	c = comment
	while context and c.level > 1:
		c.parent_comment.replies2 = [c]
		c = c.parent_comment
		context -= 1
	top_comment = c

	if v: defaultsortingcomments = v.defaultsortingcomments
	else: defaultsortingcomments = "new"
	sort=request.values.get("sort", defaultsortingcomments)

	if v:
		votes = g.db.query(CommentVote).filter_by(user_id=v.id).subquery()

		blocking = v.blocking.subquery()

		blocked = v.blocked.subquery()

		comments = g.db.query(
			Comment,
			votes.c.vote_type,
			blocking.c.target_id,
			blocked.c.target_id,
		)

		if not (v and v.shadowbanned) and not (v and v.admin_level >= 3):
			comments = comments.join(User, User.id == Comment.author_id).filter(User.shadowbanned == None)
		 
		comments=comments.filter(
			Comment.parent_submission == post.id
		).join(
			votes,
			votes.c.comment_id == Comment.id,
			isouter=True
		).join(
			blocking,
			blocking.c.target_id == Comment.author_id,
			isouter=True
		).join(
			blocked,
			blocked.c.user_id == Comment.author_id,
			isouter=True
		)

		output = []
		for c in comments:
			comment = c[0]
			comment.voted = c[1] or 0
			comment.is_blocking = c[2] or 0
			comment.is_blocked = c[3] or 0
			output.append(comment)

	post.replies=[top_comment]
			
	if request.headers.get("Authorization"): return top_comment.json
	else: 
		if post.state_mod != StateMod.VISIBLE and not (v and (v.admin_level >= 2 or post.author_id == v.id)): template = "submission_banned.html"
		else: template = "submission.html"
		return render_template(template, v=v, p=post, sort=sort, comment_info=comment_info, render_replies=True)

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
	if not parent_post: abort(404) # don't allow sending comments to the ether
	level = 1 if isinstance(parent, Submission) else parent.level + 1

	body = sanitize_raw(request.values.get("body"), allow_newlines=True, length_limit=COMMENT_BODY_LENGTH_MAXIMUM)
	if not body and not request.files.get('file'): 
		abort(400, "You need to actually write something!")

	if request.files.get("file") and request.headers.get("cf-ipcountry") != "T1":
		files = request.files.getlist('file')[:4]
		for file in files:
			if file.content_type.startswith('image/'):
				oldname = f'/images/{time.time()}'.replace('.','') + '.webp'
				file.save(oldname)
				image = process_image(oldname)
				if image == "":
					abort(500, "Image upload failed")

				if app.config['MULTIMEDIA_EMBEDDING_ENABLED']:
					body += f"\n\n![]({image})"
				else:
					body += f'\n\n<a href="{image}">{image}</a>'
			else: abort(400, "Image files only")

	body_html = sanitize(body, comment=True)

	existing = g.db.query(Comment.id).filter(
		Comment.author_id == v.id,
		Comment.state_user_deleted_utc == None,
		Comment.parent_comment_id == parent_comment_id,
		Comment.parent_submission == parent_post.id,
		Comment.body_html == body_html
	).one_or_none()

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
		).all()

		threshold = app.config["COMMENT_SPAM_COUNT_THRESHOLD"]
		if v.age_seconds >= (60 * 60 * 24 * 7):
			threshold *= 3
		elif v.age_seconds >= (60 * 60 * 24):
			threshold *= 2

		if len(similar_comments) > threshold:
			text = "Your account has been banned for **1 day** for the following reason:\n\n> Too much spam!"
			send_repeatable_notification(v.id, text)

			v.ban(reason="Spamming.",
					days=1)

			for comment in similar_comments:
				comment.state_mod = StateMod.REMOVED
				comment.state_mod_set_by = "AutoJanny"
				g.db.add(comment)
				ma=ModAction(
					user_id=AUTOJANNY_ID,
					target_comment_id=comment.id,
					kind="remove_comment",
					_note="spam"
					)
				g.db.add(ma)

			abort(403, "Too much spam!")

	is_filtered = v.should_comments_be_filtered()

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
				body=body[:COMMENT_BODY_LENGTH_MAXIMUM],
				ghost=parent_post.ghost,
				state_mod=StateMod.FILTERED if is_filtered else StateMod.VISIBLE,
				)

	c.upvotes = 1
	g.db.add(c)
	g.db.flush()

	if c.level == 1: c.top_comment_id = c.id
	else: c.top_comment_id = parent.top_comment_id

	if not v.shadowbanned and not is_filtered:
		comment_on_publish(c)

	vote = CommentVote(user_id=v.id,
						 comment_id=c.id,
						 vote_type=1,
						 )
	g.db.add(vote)

	c.voted = 1

	g.db.commit()

	if request.headers.get("Authorization"): return c.json
	
	if replying_to_blocked:
		message = "This user has blocked you. You are still welcome to reply " \
				  "but you will be held to a higher standard of civility than you would be otherwise"
	elif (v.admin_level <= PERMS['POST_COMMENT_MODERATION'] 
			and len(body) > COMMENT_BODY_LENGTH_MAXIMUM_UNFILTERED):
		message = "Your comment has been submitted but is a bit long, so it's pending approval."
	else:
		message = None
	return {"comment": render_template("comments.html", v=v, comments=[c], ajax=True, parent_level=level), "message": message}

@app.post("/edit_comment/<cid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def edit_comment(cid, v):
	c = get_comment(cid, v=v)
	if c.author_id != v.id: abort(403)
	body = sanitize_raw(request.values.get("body"), allow_newlines=True, length_limit=COMMENT_BODY_LENGTH_MAXIMUM)

	if len(body) < 1 and not (request.files.get("file") and request.headers.get("cf-ipcountry") != "T1"):
		abort(400, "You have to actually type something!")

	if body != c.body or request.files.get("file") and request.headers.get("cf-ipcountry") != "T1":
		body_html = sanitize(body, edit=True)

		# Spam Checking
		now = int(time.time())
		cutoff = now - 60 * 60 * 24

		similar_comments = g.db.query(Comment
		).filter(
			Comment.author_id == v.id,
			Comment.body.op(
				'<->')(body) < app.config["SPAM_SIMILARITY_THRESHOLD"],
			Comment.created_utc > cutoff
		).all()

		threshold = app.config["SPAM_SIMILAR_COUNT_THRESHOLD"]
		if v.age_seconds >= (60 * 60 * 24 * 30):
			threshold *= 4
		elif v.age_seconds >= (60 * 60 * 24 * 7):
			threshold *= 3
		elif v.age_seconds >= (60 * 60 * 24):
			threshold *= 2

		if len(similar_comments) > threshold:
			text = "Your account has been banned for **1 day** for the following reason:\n\n> Too much spam!"
			send_repeatable_notification(v.id, text)

			v.ban(reason="Spamming.",
					days=1)

			for comment in similar_comments:
				comment.state_mod = StateMod.REMOVED
				comment.state_mod_set_by = "AutoJanny"
				g.db.add(comment)

			abort(403, "Too much spam!")
		# End Spam Checking

		if request.files.get("file") and request.headers.get("cf-ipcountry") != "T1":
			files = request.files.getlist('file')[:4]
			for file in files:
				if file.content_type.startswith('image/'):
					name = f'/images/{time.time()}'.replace('.','') + '.webp'
					file.save(name)
					url = process_image(name)
					body += f"\n\n![]({url})"
				else: abort(400, "Image files only")

			body_html = sanitize(body, edit=True)

		c.body = body[:COMMENT_BODY_LENGTH_MAXIMUM]
		c.body_html = body_html

		if int(time.time()) - c.created_utc > 60 * 3: c.edited_utc = int(time.time())

		g.db.add(c)
		
		if c.state_mod == StateMod.VISIBLE:
			notify_users = NOTIFY_USERS(body, v)

			for x in notify_users:
				notif = g.db.query(Notification) \
					.filter_by(comment_id=c.id, user_id=x).one_or_none()
				if not notif:
					n = Notification(comment_id=c.id, user_id=x)
					g.db.add(n)

		g.db.commit()

	return {"comment": c.realbody(v)}


@app.post("/delete/comment/<cid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def delete_comment(cid, v):
	c = get_comment(cid, v=v)
	if c.state_user_deleted_utc: abort(409)
	if c.author_id != v.id: abort(403)
	c.state_user_deleted_utc = datetime.now(tz=timezone.utc)
	# TODO: update stateful counters
	g.db.add(c)
	g.db.commit()

	return {"message": "Comment deleted!"}

@app.post("/undelete/comment/<cid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def undelete_comment(cid, v):
	c = get_comment(cid, v=v)
	if not c.state_user_deleted_utc: abort(409)
	if c.author_id != v.id: abort(403)
	c.state_user_deleted_utc = None
	# TODO: update stateful counters
	g.db.add(c)
	g.db.commit()

	return {"message": "Comment undeleted!"}


@app.post("/pin_comment/<cid>")
@auth_required
def pin_comment(cid, v):
	comment = get_comment(cid, v=v)
	
	if not comment.is_pinned:
		if v.id != comment.post.author_id: abort(403)
		
		if comment.post.ghost: comment.is_pinned = "(OP)"
		else: comment.is_pinned = v.username + " (OP)"

		g.db.add(comment)

		if v.id != comment.author_id:
			if comment.post.ghost: message = f"OP has pinned your [comment]({comment.shortlink})!"
			else: message = f"@{v.username} (OP) has pinned your [comment]({comment.shortlink})!"
			send_repeatable_notification(comment.author_id, message)

		g.db.commit()
	return {"message": "Comment pinned!"}
	

@app.post("/unpin_comment/<cid>")
@auth_required
def unpin_comment(cid, v):
	
	comment = get_comment(cid, v=v)
	
	if comment.is_pinned:
		if v.id != comment.post.author_id: abort(403)

		if not comment.is_pinned.endswith(" (OP)"): 
			abort(403, "You can only unpin comments you have pinned!")

		comment.is_pinned = None
		g.db.add(comment)

		if v.id != comment.author_id:
			message = f"@{v.username} (OP) has unpinned your [comment]({comment.shortlink})!"
			send_repeatable_notification(comment.author_id, message)
		g.db.commit()
	return {"message": "Comment unpinned!"}


@app.post("/save_comment/<cid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def save_comment(cid, v):
	comment=get_comment(cid)

	save=g.db.query(CommentSaveRelationship).filter_by(user_id=v.id, comment_id=comment.id).one_or_none()

	if not save:
		new_save=CommentSaveRelationship(user_id=v.id, comment_id=comment.id)
		g.db.add(new_save)

		g.db.commit()

	return {"message": "Comment saved!"}

@app.post("/unsave_comment/<cid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def unsave_comment(cid, v):
	comment=get_comment(cid)

	save=g.db.query(CommentSaveRelationship).filter_by(user_id=v.id, comment_id=comment.id).one_or_none()

	if save:
		g.db.delete(save)
		g.db.commit()

	return {"message": "Comment unsaved!"}
