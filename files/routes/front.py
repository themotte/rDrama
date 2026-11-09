import files.helpers.listing as listing
from files.__main__ import app, limiter
from files.classes.submission import Submission
from files.classes.visstate import StateMod
from files.helpers.contentsorting import apply_time_filter, sort_objects
from files.helpers.get import *
from files.helpers.notifications import not_blocked_by, read_conversations, shadowban_shown_to, shown_notifications
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
	items = shown_notifications(g.db.query(Notification, Comment).join(Comment, Notification.comment_id == Comment.id), v).filter(
		Notification.read == False,
		Comment.author_id != AUTOJANNY_ID,
	).order_by(Notification.created_datetimez.desc(), Notification.comment_id.desc()).all()

	for n, c in items:
		n.read = True
		g.db.add(n)
	g.db.commit()

	return {"data":[listing.comment_json_for(c, v) for _, c in items]}


@app.get("/notifications")
@auth_required
def notifications_main(v: User):
	page = listing.request_page()

	notifications = (shown_notifications(g.db.query(Notification).join(Notification.comment), v)
		.filter(Comment.author_id != AUTOJANNY_ID)
		.order_by(Notification.created_datetimez.desc(), Notification.comment_id.desc())
		.offset(25 * (page - 1)).limit(26).all())

	next_exists = (len(notifications) > 25)
	notifications = notifications[:25]

	# With the viewer's votes and blocks
	loaded = {c.id: c for c in get_comments([n.comment_id for n in notifications], v)}
	items: list[Comment] = [loaded[n.comment_id] for n in notifications]
	# Messages' first messages, which their reply boxes ask about, loaded at once; the session holds rows only while they're referenced, so this one lives until the page renders
	tops = g.db.query(Comment).filter(Comment.id.in_({c.top_comment_id for c in items if c.is_message and c.top_comment_id})).all()
	for c, n in zip(items, notifications):
		c.notif_utc = n.created_utc
		c.unread = not n.read
		n.read = True

	# TODO: commit after request rendered, then default session expiry is fine
	g.db.expire_on_commit = False
	g.db.commit()
	g.db.expire_on_commit = True

	if request.headers.get("Authorization"):
		return {"data": [listing.comment_json_for(x, v) for x in items]}

	return render_template("notifications.html",
		v=v,
		notifications=items,
		next_exists=next_exists,
		page=page,
		standalone=True,
		render_replies=False,
		is_notification_page=True,
	)


@app.get("/notifications/posts")
@auth_required
def notifications_posts(v: User):
	page = listing.request_page()

	notifications = (g.db.query(Notification, Comment)
		.join(Comment, Notification.comment_id == Comment.id)
		.filter(Notification.user_id == v.id, Comment.author_id == AUTOJANNY_ID)
		.order_by(Notification.created_datetimez.desc(), Notification.comment_id.desc()).offset(25 * (page - 1)).limit(26).all())

	next_exists = (len(notifications) > 25)
	items = []
	for n, c in notifications[:25]:
		if not n.read:
			n.read = True
			c.unread = True
		c.notif_utc = n.created_utc
		items.append(c)

	g.db.commit()

	if request.headers.get("Authorization"):
		return {"data": [x.json_for(v, without_replies=True) for x in items]}

	return render_template("notifications.html",
		v=v,
		notifications=items,
		next_exists=next_exists,
		page=page,
		standalone=True,
		render_replies=False,
		is_notification_page=True,
	)


@app.get("/notifications/modmail")
@admin_level_required(2)
def notifications_modmail(v: User):
	page = listing.request_page()

	comments = (g.db.query(Comment)
		.filter(Comment.sentto == MODMAIL_ID, Comment.parent_submission == None, Comment.level == 1)
		.order_by(Comment.id.desc()).offset(25 * (page - 1)).limit(26).all())
	next_exists = (len(comments) > 25)
	items = read_conversations(comments[:25], v)

	return render_template("notifications.html",
		v=v,
		notifications=items,
		next_exists=next_exists,
		page=page,
		standalone=True,
		render_replies=True,
		is_notification_page=True,
	)


@app.get("/notifications/messages")
@auth_required
def notifications_messages(v: User):
	page = listing.request_page()

	comments = g.db.query(Comment).filter(
		Comment.sentto != None,
		or_(Comment.author_id==v.id, Comment.sentto==v.id),
		Comment.parent_submission == None,
		Comment.level == 1,
		not_blocked_by(v),
	)

	comments = comments.filter(shadowban_shown_to(v)).order_by(Comment.id.desc()).offset(25 * (page - 1)).limit(26).all()

	next_exists = (len(comments) > 25)
	items = read_conversations(comments[:25], v)

	if request.headers.get("Authorization"):
		return {"data": [x.json_for(v) for x in items]}

	return render_template("notifications.html",
		v=v,
		notifications=items,
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
def front_all(v):
	page = listing.request_page()

	sort = listing.request_sort(v.defaultsorting if v and v.defaultsorting in SORTS_POSTS else "new")
	t = listing.request_time_filter()

	try: gt=int(request.values.get("after", 0))
	except: gt=0

	try: lt=int(request.values.get("before", 0))
	except: lt=0

	ids, next_exists = listing.frontlist(sort=sort,
					page=page,
					t=t,
					v=v,
					filter_words=v.filter_words if v else [],
					gt=gt,
					lt=lt,
					)

	posts = get_posts(ids, v=v)
	
	if request.headers.get("Authorization"): return {"data": [listing.post_json_for(x, v) for x in posts], "next_exists": next_exists}
	return render_template("home.html", v=v, listing=posts, next_exists=next_exists, sort=sort, t=t, page=page, home=True)


@app.get("/changelog")
@auth_required
def changelog(v):
	page = listing.request_page()

	sort = listing.request_sort("new")
	t = listing.request_time_filter()

	ids = listing.changeloglist(sort=sort,
					page=page,
					t=t,
					v=v,
					)

	next_exists = (len(ids) > 25)
	ids = ids[:25]

	posts = get_posts(ids, v=v)

	if request.headers.get("Authorization"): return {"data": [listing.post_json_for(x, v) for x in posts], "next_exists": next_exists}
	return render_template("changelog.html", v=v, listing=posts, next_exists=next_exists, sort=sort, t=t, page=page)


@app.get("/random_post")
def random_post():
	p = listing.listable_posts(g.db.query(Submission.id), None).order_by(func.random()).first()

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
	page = listing.request_page()
	sort = listing.request_sort("new")
	time_filter = listing.request_time_filter()
	time_gt = request.values.get("after", 0, int)
	time_lt = request.values.get("before", 0, int)

	idlist = get_comments_idlist(v=v,
		page=page, sort=sort, t=time_filter, gt=time_gt, lt=time_lt)
	next_exists = len(idlist) > 25
	idlist = idlist[:25]

	comments = get_comments(idlist, v=v)

	if request.headers.get("Authorization"):
		return {"data": [listing.comment_json_for(x, v) for x in comments]}
	return render_template("home_comments.html", v=v,
		sort=sort, t=time_filter, page=page, next_exists=next_exists,
		comments=comments, standalone=True)


def get_comments_idlist(page=1, v=None, sort="new", t="all", gt=0, lt=0):
	comments = listing.listable_comments(g.db.query(Comment.id), v)

	if gt: comments = comments.filter(Comment.created_utc > gt)
	if lt: comments = comments.filter(Comment.created_utc < lt)

	if not gt and not lt:
		comments = apply_time_filter(comments, t, Comment)
	comments = sort_objects(comments, sort, Comment)

	comments = comments.offset(25 * (page - 1)).limit(26).all()
	return [x[0] for x in comments]
