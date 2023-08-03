from sqlalchemy.orm import Query

import files.helpers.listing as listing
from files.__main__ import app, limiter
from files.classes.submission import Submission
from files.classes.visstate import StateMod
from files.helpers.comments import comment_filter_moderated
from files.helpers.contentsorting import (apply_time_filter,
                                          sort_comment_results, sort_objects)
from files.helpers.config.environment import DEFAULT_TIME_FILTER
from files.helpers.get import *
from files.helpers.wrappers import *

@app.post("/clear")
@auth_required
def clear(v):
	notifs = g.db.query(Notification).join(Comment, Notification.comment_id == Comment.id).filter(Notification.read == False, Notification.user_id == v.id).all()
	for n in notifs:
		n.read = True
		g.db.add(n)
	g.db.commit()
	return {"message": "Notifications cleared!"}

@app.get("/unread")
@auth_required
def unread(v):
	listing = g.db.query(Notification, Comment).join(Comment, Notification.comment_id == Comment.id).filter(
		Notification.read == False,
		Notification.user_id == v.id,
		Comment.state_mod == StateMod.VISIBLE,
		Comment.state_user_deleted_utc == None,
		Comment.author_id != AUTOJANNY_ID,
	).order_by(Notification.created_datetimez.desc()).all()

	for n, c in listing:
		n.read = True
		g.db.add(n)
	g.db.commit()

	return {"data":[x[1].json for x in listing]}


@app.get("/notifications")
@auth_required
def notifications_main(v: User):
	page: int = max(request.values.get("page", 1, int) or 1, 1)

	comments = (g.db.query(Comment, Notification)
		.join(Notification.comment)
		.filter(
			Notification.user_id == v.id,
			Comment.state_mod == StateMod.VISIBLE,
			Comment.state_user_deleted_utc == None,
			Comment.author_id != AUTOJANNY_ID,
		).order_by(Notification.created_datetimez.desc()))

	if not v.shadowbanned and v.admin_level < 3:
		comments = comments.join(Comment.author).filter(User.shadowbanned == None)

	comments = comments.offset(25 * (page - 1)).limit(26).all()

	next_exists = (len(comments) > 25)
	comments = comments[:25]

	for c, n in comments:
		c.notif_utc = n.created_utc
		c.unread = not n.read
		n.read = True

	listing: list[Comment] = [c for c, _ in comments]

	# TODO: commit after request rendered, then default session expiry is fine
	g.db.expire_on_commit = False
	g.db.commit()
	g.db.expire_on_commit = True

	if request.headers.get("Authorization"):
		return {"data": [x.json for x in listing]}

	return render_template("notifications.html",
		v=v,
		notifications=listing,
		next_exists=next_exists,
		page=page,
		standalone=True,
		render_replies=False,
		is_notification_page=True,
	)


@app.get("/notifications/posts")
@auth_required
def notifications_posts(v: User):
	page: int = max(request.values.get("page", 1, int) or 1, 1)

	notifications = (g.db.query(Notification, Comment)
		.join(Comment, Notification.comment_id == Comment.id)
		.filter(Notification.user_id == v.id, Comment.author_id == AUTOJANNY_ID)
		.order_by(Notification.created_datetimez.desc()).offset(25 * (page - 1)).limit(101).all())

	listing = []

	for index, x in enumerate(notifications[:100]):
		n, c = x
		if n.read and index > 24: break
		elif not n.read:
			n.read = True
			c.unread = True
			g.db.add(n)
		if n.created_utc > 1620391248: c.notif_utc = n.created_utc
		listing.append(c)

	next_exists = (len(notifications) > len(listing))

	g.db.commit()

	if request.headers.get("Authorization"):
		return {"data": [x.json for x in listing]}

	return render_template("notifications.html",
		v=v,
		notifications=listing,
		next_exists=next_exists,
		page=page,
		standalone=True,
		render_replies=True,
		is_notification_page=True,
	)


@app.get("/notifications/modmail")
@admin_level_required(2)
def notifications_modmail(v: User):
	page: int = max(request.values.get("page", 1, int) or 1, 1)

	comments = (g.db.query(Comment)
		.filter(Comment.sentto == MODMAIL_ID)
		.order_by(Comment.id.desc()).offset(25 * (page - 1)).limit(26).all())
	next_exists = (len(comments) > 25)
	listing = comments[:25]

	if request.headers.get("Authorization"):
		return {"data": [x.json for x in listing]}

	return render_template("notifications.html",
		v=v,
		notifications=listing,
		next_exists=next_exists,
		page=page,
		standalone=True,
		render_replies=True,
		is_notification_page=True,
	)


@app.get("/notifications/messages")
@auth_required
def notifications_messages(v: User):
	page: int = max(request.values.get("page", 1, int) or 1, 1)

	comments = g.db.query(Comment).filter(
		Comment.sentto != None,
		or_(Comment.author_id==v.id, Comment.sentto==v.id),
		Comment.parent_submission == None,
		Comment.level == 1,
	)

	if not v.shadowbanned and v.admin_level < 3:
		comments = comments.join(Comment.author).filter(User.shadowbanned == None)

	comments = comments.order_by(Comment.id.desc()).offset(25 * (page - 1)).limit(26).all()

	next_exists = (len(comments) > 25)
	listing = comments[:25]

	if request.headers.get("Authorization"):
		return {"data": [x.json for x in listing]}

	return render_template("notifications.html",
		v=v,
		notifications=listing,
		next_exists=next_exists,
		page=page,
		standalone=True,
		render_replies=True,
		is_notification_page=True,
	)


@app.get("/")
@app.get("/catalog")
@limiter.limit("3/second;30/minute;1000/hour;5000/day")
@auth_desired
def front_all(v, subdomain=None):
	if g.webview and not session.get("session_id"):
		session["session_id"] = secrets.token_hex(49)

	try: page = max(int(request.values.get("page", 1)), 1)
	except: abort(400)

	if v:
		defaultsorting = v.defaultsorting
		defaulttime = 'all'
	else:
		defaultsorting = "new"
		defaulttime = 'all'

	sort=request.values.get("sort", defaultsorting)
	t=request.values.get('t', defaulttime)
	ccmode=request.values.get('ccmode', "false").lower()

	if sort == 'bump': t='all'
	
	try: gt=int(request.values.get("after", 0))
	except: gt=0

	try: lt=int(request.values.get("before", 0))
	except: lt=0

	ids, next_exists = listing.frontlist(sort=sort,
					page=page,
					t=t,
					v=v,
					ccmode=ccmode,
					filter_words=v.filter_words if v else [],
					gt=gt,
					lt=lt,
					)

	posts = get_posts(ids, v=v, eager=True)
	
	if v:
		if v.hidevotedon: posts = [x for x in posts if not hasattr(x, 'voted') or not x.voted]

		if v.patron_utc and v.patron_utc < time.time():
			v.patron = 0
			v.patron_utc = 0
			send_repeatable_notification(v.id, "Your paypig status has expired!")
			g.db.add(v)
			g.db.commit()
		if v.unban_utc and v.unban_utc < time.time():
			v.is_banned = 0
			v.unban_utc = 0
			v.ban_evade = 0
			send_repeatable_notification(v.id, "You have been unbanned!")
			g.db.add(v)
			g.db.commit()

	if request.headers.get("Authorization"): return {"data": [x.json for x in posts], "next_exists": next_exists}
	return render_template("home.html", v=v, listing=posts, next_exists=next_exists, sort=sort, t=t, page=page, ccmode=ccmode, home=True)


@app.get("/changelog")
@auth_required
def changelog(v):
	try: page = max(int(request.values.get("page", 1)), 1)
	except: page = 1

	sort=request.values.get("sort", "new")
	t=request.values.get('t', "all")

	ids = listing.changeloglist(sort=sort,
					page=page,
					t=t,
					v=v,
					)

	next_exists = (len(ids) > 25)
	ids = ids[:25]

	posts = get_posts(ids, v=v)

	if request.headers.get("Authorization"): return {"data": [x.json for x in posts], "next_exists": next_exists}
	return render_template("changelog.html", v=v, listing=posts, next_exists=next_exists, sort=sort, t=t, page=page)


@app.get("/random_post")
def random_post():
	p = g.db.query(Submission.id).filter(Submission.state_user_deleted_utc == None, Submission.state_mod == StateMod.VISIBLE, Submission.private == False).order_by(func.random()).first()

	if p: p = p[0]
	else: abort(404)

	return redirect(f"/post/{p}")


@app.get("/random_user")
def random_user():
	u = g.db.query(User.username).order_by(func.random()).first()
	
	if u: u = u[0]
	else: abort(404)

	return redirect(f"/@{u}")


@app.get("/comments")
@auth_required
def all_comments(v):
	page = max(request.values.get("page", 1, int), 1)
	sort = request.values.get("sort", "new")
	time_filter = request.values.get("t", DEFAULT_TIME_FILTER)
	time_gt = request.values.get("after", 0, int)
	time_lt = request.values.get("before", 0, int)

	idlist = get_comments_idlist(v=v,
		page=page, sort=sort, t=time_filter, gt=time_gt, lt=time_lt)
	next_exists = len(idlist) > 25
	idlist = idlist[:25]

	def comment_tree_filter(q: Query) -> Query:
		q = q.filter(Comment.id.in_(idlist))
		q = comment_filter_moderated(q, v)
		q = q.options(selectinload(Comment.post)) # used for post titles
		return q

	comments, _ = get_comment_trees_eager(comment_tree_filter, sort=sort, v=v)
	comments = sort_comment_results(comments, sort=sort, pins=False)

	if request.headers.get("Authorization"):
		return {"data": [x.json for x in comments]}
	return render_template("home_comments.html", v=v,
		sort=sort, t=time_filter, page=page, next_exists=next_exists,
		comments=comments, standalone=True)


def get_comments_idlist(page=1, v=None, sort="new", t="all", gt=0, lt=0):
	comments = g.db.query(Comment.id) \
		.join(Comment.post) \
		.join(Comment.author) \
		.filter(Comment.parent_submission != None)

	if v.admin_level < 2:
		comments = comments.filter(
			Comment.author_id.notin_(v.userblocks),
			Comment.state_mod == StateMod.VISIBLE,
			Comment.state_user_deleted_utc == None,
			Submission.private == False, # comment parent post not private
			User.shadowbanned == None, # comment author not shadowbanned
		)

	if gt: comments = comments.filter(Comment.created_utc > gt)
	if lt: comments = comments.filter(Comment.created_utc < lt)

	if not gt and not lt:
		comments = apply_time_filter(comments, t, Comment)
	comments = sort_objects(comments, sort, Comment)

	comments = comments.offset(25 * (page - 1)).limit(26).all()
	return [x[0] for x in comments]
