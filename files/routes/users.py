import io
import time
from collections import Counter

import qrcode
from sqlalchemy.orm import Query

import files.helpers.listing as listings
from files.__main__ import app, cache, limiter
from files.classes.leaderboard import (GIVEN_UPVOTES_META,
                                       GivenUpvotesLeaderboard, LeaderboardMeta,
                                       RECEIVED_DOWNVOTES_META,
                                       ReceivedDownvotesLeaderboard,
                                       SimpleLeaderboard, UserBlockLeaderboard)
from files.classes.visstate import StateMod
from files.helpers.alerts import *
from files.helpers.config.const import *
from files.helpers.contentsorting import (apply_time_filter, sort_objects)
from files.helpers.media import new_image_path, process_image
from files.helpers.config.regex import valid_username_regex
from files.helpers.sanitize import *
from files.mail import *
from files.routes.importstar import *


# Each voter list: (vote type, whether it ranks the voters on the user's content rather than the authors of what the user voted on, heading)
_VOTER_LISTS = {
	"upvoters": (1, True, "Who upvotes @{}"),
	"downvoters": (-1, True, "Who downvotes @{}"),
	"upvoting": (1, False, "Who @{} upvotes"),
	"downvoting": (-1, False, "Who @{} downvotes"),
}
_VOTER_LIST_NAMES = ",".join(_VOTER_LISTS)


def _visible(cls):
	visible = (cls.ghost == False, cls.state_mod == StateMod.VISIBLE, cls.state_user_deleted_utc == None)
	return (*visible, cls.private == False) if cls is Submission else visible


@app.get(f"/@<username>/<any({_VOTER_LIST_NAMES}):list_name>/<uid>/<any(posts,comments):kind>")
@admin_level_required(3)
def voted_content(v, username, list_name, uid, kind):
	u = get_user(username)
	uid = parse_id(uid)
	if uid is None: abort(404)
	vote_type, on_users_content, _ = _VOTER_LISTS[list_name]
	author_id, voter_id = (u.id, uid) if on_users_content else (uid, u.id)

	page = listings.request_page()

	if kind == "posts":
		cls, vote_cls, voted_id = Submission, Vote, Vote.submission_id
	else:
		cls, vote_cls, voted_id = Comment, CommentVote, CommentVote.comment_id
	listing = g.db.query(cls.id).join(vote_cls, voted_id == cls.id).filter(*_visible(cls), vote_cls.vote_type == vote_type, cls.author_id == author_id, vote_cls.user_id == voter_id).order_by(cls.created_utc.desc()).offset(25 * (page - 1)).limit(26).all()

	listing = [x[0] for x in listing]
	next_exists = len(listing) > 25
	listing = listing[:25]

	if kind == "posts":
		return render_template("voted_posts.html", next_exists=next_exists, listing=get_posts(listing, v=v), page=page, v=v)
	return render_template("voted_comments.html", next_exists=next_exists, listing=get_comments(listing, v=v), page=page, v=v, standalone=True)


@app.get(f"/@<username>/<any({_VOTER_LIST_NAMES}):list_name>")
@admin_level_required(3)
def voters(v, username, list_name):
	id = get_user(username).id
	vote_type, on_users_content, heading = _VOTER_LISTS[list_name]

	counts = Counter()
	for cls, vote_cls, voted_id in ((Submission, Vote, Vote.submission_id), (Comment, CommentVote, CommentVote.comment_id)):
		other, this = (vote_cls.user_id, cls.author_id) if on_users_content else (cls.author_id, vote_cls.user_id)
		counts += Counter(dict(g.db.query(other, func.count(other)).select_from(cls).join(vote_cls, voted_id == cls.id).filter(*_visible(cls), vote_cls.vote_type == vote_type, this == id).group_by(other).all()))

	users = g.db.query(User).filter(User.id.in_(counts.keys())).all()
	users = sorted(((user, counts[user.id]) for user in users), key=lambda x: (-x[1], x[0].id))

	ranked_ids = [user.id for user, _ in users]
	if v.id in ranked_ids:
		position = ranked_ids.index(v.id)
		pos = (position + 1, users[position][1])
	else:
		pos = (len(users) + 1, 0)

	return render_template("voters.html", v=v, users=users[:25], pos=pos, name='Up' if vote_type == 1 else 'Down', name2=heading.format(username))


@app.get("/leaderboard")
@admin_level_required(2)
def leaderboard(v:User):
	users:Query = g.db.query(User)

	subscribers = SimpleLeaderboard(v, LeaderboardMeta("Followers", "followers", "followers", "Followers", "followers"), g.db, users, User.stored_subscriber_count)
	posts = SimpleLeaderboard(v, LeaderboardMeta("Posts", "post count", "posts", "Posts", "posts"), g.db, users, User.post_count)
	comments = SimpleLeaderboard(v, LeaderboardMeta("Comments", "comment count", "comments", "Comments", ""), g.db, users, User.comment_count)
	truescore = SimpleLeaderboard(v, LeaderboardMeta("Truescore", "truescore", "truescore", "Truescore", None), g.db, users, User.truescore)
	blocks = UserBlockLeaderboard(v, LeaderboardMeta("Blocked", "most blocked", "blocked", "Blocked By", None), g.db)

	leaderboards = [truescore, subscribers, posts, comments, blocks]

	# The downvotes-received / upvotes-given leaderboards are expensive full-table
	# aggregations, so they're precomputed once a day by the leaderboard_recalc
	# cron job and cached. Rebuild them cheaply from the cache here, and skip them
	# if the cron job hasn't populated the cache yet.
	lb_downvotes_received = ReceivedDownvotesLeaderboard.from_cache(RECEIVED_DOWNVOTES_META, g.db, cache)
	lb_upvotes_given = GivenUpvotesLeaderboard.from_cache(GIVEN_UPVOTES_META, g.db, cache)
	if lb_downvotes_received is not None and lb_upvotes_given is not None:
		leaderboards.extend([lb_downvotes_received, lb_upvotes_given])

	return render_template("leaderboard.html", v=v, leaderboards=leaderboards)

@app.get("/@<username>/profilecss")
def get_profilecss(username):
	user = get_user(username)
	return Response(user.profilecss or "", mimetype="text/css")

def _subscribable_post(post_id:str, v:User) -> Submission:
	post = get_post(post_id)
	if post.is_draft_hidden_from(v): abort(404)
	return post


@app.post("/subscribe/<post_id>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def subscribe(v, post_id):
	post = _subscribable_post(post_id, v)
	if not g.db.get(Subscription, (v.id, post.id)):
		g.db.add(Subscription(user_id=v.id, submission_id=post.id))
		g.db.commit()
	return {"message": "Post subscribed!"}
	
@app.post("/unsubscribe/<post_id>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def unsubscribe(v, post_id):
	post = _subscribable_post(post_id, v)
	sub = g.db.get(Subscription, (v.id, post.id))
	if sub:
		g.db.delete(sub)
		g.db.commit()
	return {"message": "Post unsubscribed!"}

@app.post("/@<username>/message")
@limiter.limit("1/second;10/minute;20/hour;50/day")
@auth_required
def message2(v, username):
	if v.is_suspended_permanently:
		abort(403, "You have been permabanned and cannot send messages; " + \
			"contact modmail if you think this decision was incorrect.")

	user = get_user(username, v=v, include_blocks=True)

	if user.id == MODMAIL_ID:
		abort(403, "Please use modmail to contact the admins")

	if not v.can_send_messages and user.admin_level < PERMS['POST_COMMENT_MODERATION']:
		abort(403, MESSAGE_CONTRIBUTION_REQUIRED)

	if hasattr(user, 'is_blocking') and user.is_blocking: abort(403, "You're blocking this user.")

	if v.admin_level <= 1 and hasattr(user, 'is_blocked') and user.is_blocked:
		abort(403, "This user is blocking you.")

	message = request.values.get("message", "").strip()[:MESSAGE_BODY_LENGTH_MAXIMUM].strip()

	if not message: abort(400, "Message is empty!")
	body_html = sanitize(message)

	existing = g.db.query(Comment.id).filter(Comment.author_id == v.id,
															Comment.sentto == user.id,
															Comment.body_html == body_html,
															).one_or_none()

	if existing: abort(403, "Message already exists.")

	c = Comment(author_id=v.id,
						  parent_submission=None,
						  level=1,
						  sentto=user.id,
						  body_html=body_html,
						  state_mod=StateMod.VISIBLE,
						  )
	g.db.add(c)
	g.db.flush()

	c.top_comment_id = c.id

	g.db.add(Notification(comment_id=c.id, user_id=user.id))

	g.db.commit()

	return {"message": "Message sent!"}


@app.post("/reply")
@limiter.limit("1/second;6/minute;50/hour;200/day")
@auth_required
def messagereply(v):
	message = request.values.get("body", "").strip()[:MESSAGE_BODY_LENGTH_MAXIMUM].strip()

	if not message and not request.files.get("file"): abort(400, "Message is empty!")

	if not request.values.get("parent_id"): abort(400, "Which message are you replying to?")
	parent = get_comment(request.values["parent_id"], v=v)
	if not parent.takes_part_in_thread(v): abort(403, "You can only reply in your own conversations.")
	top = parent.thread_top
	modmail = top.sentto == MODMAIL_ID
	# The recipient: modmail throughout a modmail thread, else the other of the conversation's two users
	if modmail: recipient = MODMAIL_ID
	elif v.id == top.author_id: recipient = top.sentto
	else: recipient = top.author_id

	body_html = sanitize(message)

	file = request.files.get("file") if request.headers.get("cf-ipcountry") != "T1" else None
	if file and not modmail: abort(400, "Images can only be attached in modmail.")
	if file:
		if file.content_type.startswith('image/'):
			name = new_image_path()
			file.save(name)
			url = process_image(name)
			body_html += f'<img data-bs-target="#expandImageModal" data-bs-toggle="modal" onclick="expandDesktopImage(this.src)" class="img" src="{url}" loading="lazy">'
		else: abort(400, "Image files only")


	c = Comment(author_id=v.id,
							parent_submission=None,
							parent_comment_id=parent.id,
							top_comment_id=parent.top_comment_id,
							level=parent.level + 1,
							sentto=recipient,
							body_html=body_html,
							state_mod=StateMod.VISIBLE,
							)
	g.db.add(c)
	g.db.flush()

	if modmail:
		notified = notify_modmail(c.id, v)
		# Admins' answers reach the starter, unless the site itself started the thread
		if v.id != top.author_id and top.author_id not in SYSTEM_ACCOUNT_IDS and top.author_id not in notified:
			g.db.add(Notification(comment_id=c.id, user_id=top.author_id))
	else:
		g.db.add(Notification(comment_id=c.id, user_id=recipient))

	g.db.commit()

	return {"comment": render_template("comments.html", v=v, comments=[c], ajax=True)}

@app.get("/2faqr/<secret>")
@auth_required
def mfa_qr(secret, v):
	x = pyotp.TOTP(secret)
	qr = qrcode.QRCode(
		error_correction=qrcode.constants.ERROR_CORRECT_L
	)
	qr.add_data(x.provisioning_uri(v.username, issuer_name=app.config["SITE_TITLE"]))
	img = qr.make_image(fill_color="#000000", back_color="white")

	mem = io.BytesIO()

	img.save(mem, format="PNG")
	mem.seek(0, 0)

	return send_file(mem, mimetype="image/png", as_attachment=False)


@app.get("/is_available/<name>")
def api_is_available(name):
	name = name.strip()
	if not valid_username_regex.fullmatch(name): return {name: False}
	taken = g.db.query(User.id).filter(or_(func.lower(User.username) == name.lower(), func.lower(User.original_username) == name.lower())).first()
	return {name: taken is None}

@app.get("/id/<int:id>")
def user_id(id:int):
	user = get_account(id)
	return redirect(user.url)

@app.get("/u/<username>")
def redditor_moment_redirect(username:str):
	return redirect(f"/@{username}")

@app.get("/@<username>/followers")
@auth_desired
def followers(v, username):
	u = get_user(username)
	users = g.db.query(User).join(Follow, Follow.target_id == u.id).filter(Follow.user_id == User.id).order_by(Follow.created_datetimez).all()
	return render_template("followers.html", v=v, u=u, users=users)

@app.get("/@<username>/following")
@auth_desired
def following(v, username):
	u = get_user(username)
	users = g.db.query(User).join(Follow, Follow.user_id == u.id).filter(Follow.target_id == User.id).order_by(Follow.created_datetimez).all()
	return render_template("following.html", v=v, u=u, users=users)

def _redirect_to_username(u:User, page:str):
	'''The same profile page, and query, under the user's current username.'''
	query = request.query_string.decode()
	return redirect(f"/@{u.username}/{page}" + (f"?{query}" if query else ""))


@app.get("/@<username>/posts")
@auth_desired
def u_username(username, v=None):
	u = get_user(username, v=v, include_blocks=True)

	if username != u.username: return _redirect_to_username(u, "posts")

	if u.reserved:
		if request.headers.get("Authorization") or request.headers.get("xhr"): abort(403, f"That username is reserved for: {u.reserved}")
		return render_template("userpage_reserved.html", u=u, v=v)

	if u.is_private and (not v or (v.id != u.id and v.admin_level < 2)):
		if request.headers.get("Authorization") or request.headers.get("xhr"): abort(403, "That userpage is private")
		return render_template("userpage_private.html", u=u, v=v, is_following=(v and u.has_follower(v)))

	
	if v and u.is_blocking:
		if request.headers.get("Authorization") or request.headers.get("xhr"): abort(403, f"You are blocking @{u.username}.")
		return render_template("userpage_blocking.html", u=u, v=v)

	sort = listings.request_sort("new")
	t = listings.request_time_filter()
	page = listings.request_page()

	shown = u.shows_activity_to(v)
	ids = listings.userpagelisting(u, v=v, page=page, sort=sort, t=t) if shown else []

	next_exists = (len(ids) > 25)
	ids = ids[:25]

	if page == 1 and shown:
		ids = listings.userpage_pinned(u, v) + ids

	listing = get_posts(ids, v=v)

	if request.headers.get("Authorization"): return {"data": [listings.post_json_for(x, v) for x in listing]}
	return render_template("userpage_submissions.html",
									u=u,
									v=v,
									listing=listing,
									page=page,
									sort=sort,
									t=t,
									next_exists=next_exists,
									is_following=(v and u.has_follower(v)))


@app.get("/@<username>/")
@auth_desired
def u_username_comments(username, v=None):
	user = get_user(username, v=v, include_blocks=True)

	if username != user.username: return _redirect_to_username(user, "")
	u = user

	if u.reserved:
		if request.headers.get("Authorization") or request.headers.get("xhr"): abort(403, f"That username is reserved for: {u.reserved}")
		return render_template("userpage_reserved.html",
												u=u,
												v=v)


	if u.is_private and (not v or (v.id != u.id and v.admin_level < 2)):
		if request.headers.get("Authorization") or request.headers.get("xhr"): abort(403, "That userpage is private")
		return render_template("userpage_private.html", u=u, v=v, is_following=(v and u.has_follower(v)))

	if v and u.is_blocking:
		if request.headers.get("Authorization") or request.headers.get("xhr"): abort(403, f"You are blocking @{u.username}.")
		return render_template("userpage_blocking.html", u=u, v=v)

	page = listings.request_page()
	
	sort = listings.request_sort("new")
	t = listings.request_time_filter()


	comments = g.db.query(Comment.id).filter(Comment.author_id == u.id, Comment.parent_submission != None)

	if not v or (v.id != u.id and v.admin_level < 2):
		comments = comments.filter(
				Comment.state_user_deleted_utc == None,
				Comment.state_mod == StateMod.VISIBLE,
				Comment.ghost == False,
				)

	# A comment on a draft would show the draft to those it's hidden from
	if not (v and v.admin_level >= PERMS['POST_COMMENT_MODERATION']):
		seen_posts = Submission.private == False
		if v: seen_posts = or_(seen_posts, Submission.author_id == v.id)
		comments = comments.join(Submission, Submission.id == Comment.parent_submission).filter(seen_posts)

	comments = apply_time_filter(comments, t, Comment)
	comments = sort_objects(comments, sort, Comment)

	ids = [x.id for x in comments.offset(25 * (page - 1)).limit(26).all()] if u.shows_activity_to(v) else []

	next_exists = (len(ids) > 25)
	ids = ids[:25]

	listing = get_comments(ids, v=v)

	is_following = (v and user.has_follower(v))

	if request.headers.get("Authorization"): return {"data": [listings.comment_json_for(c, v) for c in listing]}
	return render_template("userpage_comments.html", u=user, v=v, listing=listing, page=page, sort=sort, t=t,next_exists=next_exists, is_following=is_following, standalone=True)


def _info(user:User, v:User) -> dict:
	if user.is_blocking: abort(403, "You're blocking this user.")
	if user.is_blocked: abort(403, "This user is blocking you.")

	return user.json_for(v)


@app.get("/@<username>/info")
@auth_required
def u_username_info(username, v=None):
	return _info(get_user(username, v=v, include_blocks=True), v)

@app.get("/<id>/info")
@auth_required
def u_user_id_info(id, v=None):
	return _info(get_account(id, v=v, include_blocks=True), v)


@app.post("/follow/<username>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def follow_user(username, v):
	refuse_while_suspended(v)
	target = get_user(username, v=v, include_blocks=True)

	if target.id==v.id: abort(400, "You can't follow yourself!")

	if g.db.query(Follow).filter_by(user_id=v.id, target_id=target.id).one_or_none(): return {"message": "User followed!"}

	if target.is_nofollow: abort(403, "This user doesn't accept followers.")
	if target.is_blocked: abort(403, "This user is blocking you.")

	new_follow = Follow(user_id=v.id, target_id=target.id)
	g.db.add(new_follow)

	g.db.flush()
	target.stored_subscriber_count = g.db.query(Follow.target_id).filter_by(target_id=target.id).count()
	g.db.add(target)
	v.stored_following_count = g.db.query(Follow.target_id).filter_by(user_id=v.id).count()
	g.db.add(v)

	send_notification(target.id, f"@{v.username} has followed you!")

	g.db.commit()

	return {"message": "User followed!"}

@app.post("/unfollow/<username>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def unfollow_user(username, v):
	target = get_user(username)

	follow = g.db.query(Follow).filter_by(user_id=v.id, target_id=target.id).one_or_none()

	if follow:
		g.db.delete(follow)

		g.db.flush()
		target.stored_subscriber_count = g.db.query(Follow.target_id).filter_by(target_id=target.id).count()
		g.db.add(target)
		v.stored_following_count = g.db.query(Follow.target_id).filter_by(user_id=v.id).count()
		g.db.add(v)

		send_notification(target.id, f"@{v.username} has unfollowed you!")

		g.db.commit()

	return {"message": "User unfollowed!"}

@app.post("/remove_follow/<username>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def remove_follow(username, v):
	target = get_user(username)

	follow = g.db.query(Follow).filter_by(user_id=target.id, target_id=v.id).one_or_none()

	if not follow: return {"message": "Follower removed!"}

	g.db.delete(follow)

	g.db.flush()
	v.stored_subscriber_count = g.db.query(Follow.target_id).filter_by(target_id=v.id).count()
	g.db.add(v)
	target.stored_following_count = g.db.query(Follow.target_id).filter_by(user_id=target.id).count()
	g.db.add(target)

	send_repeatable_notification(target.id, f"@{v.username} has removed your follow!")

	g.db.commit()

	return {"message": "Follower removed!"}

@app.get("/pp/<int:id>")
@app.get("/uid/<int:id>/pic")
@app.get("/uid/<int:id>/pic/profile")
@limiter.exempt
def user_profile_uid(id:int):
	return _redirect_to_picture(get_account(id))

@app.get("/@<username>/pic")
@limiter.exempt
def user_profile_name(username:str):
	return _redirect_to_picture(get_user(username))

def _redirect_to_picture(user:User):
	r = redirect(user.profile_url)
	r.headers["Cache-Control"] = "public, max-age=300"
	return r


def _own_saved_list(v:User, username:str):
	if get_user(username).id != v.id: abort(403, "Saved lists are private.")


@app.get("/@<username>/saved/posts")
@auth_required
def saved_posts(v, username):
	_own_saved_list(v, username)
	page = listings.request_page()

	ids = v.saved_idlist()[25 * (page - 1):25 * page + 1]

	next_exists=len(ids)>25

	ids=ids[:25]

	listing = get_posts(ids, v=v)

	if request.headers.get("Authorization"): return {"data": [listings.post_json_for(x, v) for x in listing]}
	return render_template(
		"userpage_submissions.html",
		u=v,
		v=v,
		listing=listing,
		page=page,
		next_exists=next_exists,
	)


@app.get("/@<username>/saved/comments")
@auth_required
def saved_comments(v, username):
	_own_saved_list(v, username)
	page = listings.request_page()

	ids = v.saved_comment_idlist()[25 * (page - 1):25 * page + 1]

	next_exists=len(ids) > 25

	ids=ids[:25]

	listing = get_comments(ids, v=v)


	if request.headers.get("Authorization"): return {"data": [listings.comment_json_for(x, v) for x in listing]}
	return render_template(
		"userpage_comments.html",
		u=v,
		v=v,
		listing=listing,
		page=page,
		next_exists=next_exists,
		standalone=True
	)
