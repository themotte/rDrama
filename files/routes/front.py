from sqlalchemy.orm import Query

from files.helpers.wrappers import *
from files.helpers.get import *
from files.helpers.strings import sql_ilike_clean
from files.__main__ import app, cache, limiter
from files.classes.submission import Submission
from files.helpers.comments import comment_filter_moderated
from files.helpers.contentsorting import \
	apply_time_filter, sort_objects, sort_comment_results

defaulttimefilter = environ.get("DEFAULT_TIME_FILTER", "all").strip()

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
		Comment.is_banned == False,
		Comment.deleted_utc == 0,
		Comment.author_id != AUTOJANNY_ID,
	).order_by(Notification.created_utc.desc()).all()

	for n, c in listing:
		n.read = True
		g.db.add(n)
	g.db.commit()

	return {"data":[x[1].json for x in listing]}


@app.get("/notifications")
@auth_required
def notifications(v):
	try: page = max(int(request.values.get("page", 1)), 1)
	except: page = 1

	messages = request.values.get('messages')
	modmail = request.values.get('modmail')
	posts = request.values.get('posts')
	reddit = request.values.get('reddit')
	if modmail and v.admin_level > 1:
		comments = g.db.query(Comment).filter(Comment.sentto==2).order_by(Comment.id.desc()).offset(25*(page-1)).limit(26).all()
		next_exists = (len(comments) > 25)
		listing = comments[:25]
	elif messages:
		if v and (v.shadowbanned or v.admin_level > 2):
			comments = g.db.query(Comment).filter(Comment.sentto != None, or_(Comment.author_id==v.id, Comment.sentto==v.id), Comment.parent_submission == None, Comment.level == 1).order_by(Comment.id.desc()).offset(25*(page-1)).limit(26).all()
		else:
			comments = g.db.query(Comment).join(User, User.id == Comment.author_id).filter(User.shadowbanned == None, Comment.sentto != None, or_(Comment.author_id==v.id, Comment.sentto==v.id), Comment.parent_submission == None, Comment.level == 1).order_by(Comment.id.desc()).offset(25*(page-1)).limit(26).all()

		next_exists = (len(comments) > 25)
		listing = comments[:25]
	elif posts:
		notifications = g.db.query(Notification, Comment).join(Comment, Notification.comment_id == Comment.id).filter(Notification.user_id == v.id, Comment.author_id == AUTOJANNY_ID).order_by(Notification.created_utc.desc()).offset(25 * (page - 1)).limit(101).all()

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

		g.db.commit()

		next_exists = (len(notifications) > len(listing))
	elif reddit:
		notifications = g.db.query(Notification, Comment).join(Comment, Notification.comment_id == Comment.id).filter(Notification.user_id == v.id, Comment.body_html.like('%<p>New site mention: <a href="https://old.reddit.com/r/%'), Comment.parent_submission == None, Comment.author_id == NOTIFICATIONS_ID).order_by(Notification.created_utc.desc()).offset(25 * (page - 1)).limit(101).all()

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

		g.db.commit()

		next_exists = (len(notifications) > len(listing))
	else:		
		comments = g.db.query(Comment, Notification).join(Notification, Notification.comment_id == Comment.id).filter(
			Notification.user_id == v.id,
			Comment.is_banned == False,
			Comment.deleted_utc == 0,
			Comment.author_id != AUTOJANNY_ID,
			Comment.body_html.notlike('%<p>New site mention: <a href="https://old.reddit.com/r/%')
		).order_by(Notification.created_utc.desc())

		if not (v and (v.shadowbanned or v.admin_level > 2)):
			comments = comments.join(User, User.id == Comment.author_id).filter(User.shadowbanned == None)

		comments = comments.offset(25 * (page - 1)).limit(26).all()

		next_exists = (len(comments) > 25)
		comments = comments[:25]

		cids = [x[0].id for x in comments]

		comms = get_comments(cids, v=v)

		listing = []
		for c, n in comments:
			if n.created_utc > 1620391248: c.notif_utc = n.created_utc
			if not n.read:
				n.read = True
				c.unread = True
				g.db.add(n)

			if c.parent_submission:
				if c.replies2 == None:
					c.replies2 = c.child_comments.filter(or_(Comment.author_id == v.id, Comment.id.in_(cids))).all()
					for x in c.replies2:
						if x.replies2 == None: x.replies2 = []
				count = 0
				while count < 50 and c.parent_comment and (c.parent_comment.author_id == v.id or c.parent_comment.id in cids):
					count += 1
					c = c.parent_comment
					if c.replies2 == None:
						c.replies2 = c.child_comments.filter(or_(Comment.author_id == v.id, Comment.id.in_(cids))).all()
						for x in c.replies2:
							if x.replies2 == None:
								x.replies2 = x.child_comments.filter(or_(Comment.author_id == v.id, Comment.id.in_(cids))).all()
			else:
				while c.parent_comment:
					c = c.parent_comment
				c.replies2 = g.db.query(Comment).filter_by(parent_comment_id=c.id).order_by(Comment.id).all()

			if c not in listing: listing.append(c)

	g.db.commit()

	if request.headers.get("Authorization"): return {"data":[x.json for x in listing]}

	return render_template("notifications.html",
							v=v,
							notifications=listing,
							next_exists=next_exists,
							page=page,
							standalone=True,
							render_replies=True
						   )


@app.get("/")
@app.get("/catalog")
# @app.get("/h/<sub>")
# @app.get("/s/<sub>")
@limiter.limit("3/second;30/minute;1000/hour;5000/day")
@auth_desired
def front_all(v, sub=None, subdomain=None):
	if sub: sub = g.db.query(Sub).filter_by(name=sub.strip().lower()).one_or_none()
	
	if (request.path.startswith('/h/') or request.path.startswith('/s/')) and not sub: abort(404)

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

	ids, next_exists = frontlist(sort=sort,
					page=page,
					t=t,
					v=v,
					ccmode=ccmode,
					filter_words=v.filter_words if v else [],
					gt=gt,
					lt=lt,
					sub=sub,
					site=SITE
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
	return render_template("home.html", v=v, listing=posts, next_exists=next_exists, sort=sort, t=t, page=page, ccmode=ccmode, sub=sub, home=True)



@cache.memoize(timeout=86400)
def frontlist(v=None, sort='new', page=1, t="all", ids_only=True, ccmode="false", filter_words='', gt=0, lt=0, sub=None, site=None):

	posts = g.db.query(Submission)
	
	if v and v.hidevotedon:
		voted = [x[0] for x in g.db.query(Vote.submission_id).filter_by(user_id=v.id).all()]
		posts = posts.filter(Submission.id.notin_(voted))

	if not v or v.admin_level < 2:
		filter_clause = (Submission.filter_state != 'filtered') & (Submission.filter_state != 'removed')
		if v:
			filter_clause = filter_clause | (Submission.author_id == v.id)
		posts = posts.filter(filter_clause)

	if sub: posts = posts.filter_by(sub=sub.name)
	elif v: posts = posts.filter(or_(Submission.sub == None, Submission.sub.notin_(v.all_blocks)))

	if gt: posts = posts.filter(Submission.created_utc > gt)
	if lt: posts = posts.filter(Submission.created_utc < lt)

	if not gt and not lt:
		posts = apply_time_filter(posts, t, Submission)

	if (ccmode == "true"):
		posts = posts.filter(Submission.club == True)

	posts = posts.filter_by(is_banned=False, private=False, deleted_utc = 0)

	if ccmode == "false" and not gt and not lt:
		posts = posts.filter_by(stickied=None)

	if v and v.admin_level < 2:
		posts = posts.filter(Submission.author_id.notin_(v.userblocks))

	if not (v and v.changelogsub):
		posts=posts.filter(not_(Submission.title.ilike('[changelog]%')))

	if v and filter_words:
		for word in filter_words:
			word  = sql_ilike_clean(word).strip()
			posts=posts.filter(not_(Submission.title.ilike(f'%{word}%')))

	if not (v and v.shadowbanned):
		posts = posts.join(User, User.id == Submission.author_id).filter(User.shadowbanned == None)

	posts = sort_objects(posts, sort, Submission)

	if v: size = v.frontsize or 0
	else: size = 25

	posts = posts.offset(size * (page - 1)).limit(size+1).all()

	next_exists = (len(posts) > size)

	posts = posts[:size]

	if page == 1 and ccmode == "false" and not gt and not lt:
		pins = g.db.query(Submission).filter(Submission.stickied != None, Submission.is_banned == False)
		if sub: pins = pins.filter_by(sub=sub.name)
		elif v:
			pins = pins.filter(or_(Submission.sub == None, Submission.sub.notin_(v.all_blocks)))
			if v.admin_level < 2:
				pins = pins.filter(Submission.author_id.notin_(v.userblocks))

		pins = pins.all()

		for pin in pins:
			if pin.stickied_utc and int(time.time()) > pin.stickied_utc:
				pin.stickied = None
				pin.stickied_utc = None
				g.db.add(pin)
				pins.remove(pin)

		posts = pins + posts

	if ids_only: posts = [x.id for x in posts]

	g.db.commit()

	return posts, next_exists


@app.get("/changelog")
@auth_required
def changelog(v):
	try: page = max(int(request.values.get("page", 1)), 1)
	except: page = 1

	sort=request.values.get("sort", "new")
	t=request.values.get('t', "all")

	ids = changeloglist(sort=sort,
					page=page,
					t=t,
					v=v,
					site=SITE
					)

	next_exists = (len(ids) > 25)
	ids = ids[:25]

	posts = get_posts(ids, v=v)

	if request.headers.get("Authorization"): return {"data": [x.json for x in posts], "next_exists": next_exists}
	return render_template("changelog.html", v=v, listing=posts, next_exists=next_exists, sort=sort, t=t, page=page)


@cache.memoize(timeout=86400)
def changeloglist(v=None, sort="new", page=1, t="all", site=None):

	posts = g.db.query(Submission.id).filter_by(is_banned=False, private=False,).filter(Submission.deleted_utc == 0)

	if v.admin_level < 2:
		posts = posts.filter(Submission.author_id.notin_(v.userblocks))

	admins = [x[0] for x in g.db.query(User.id).filter(User.admin_level > 0).all()]
	posts = posts.filter(Submission.title.ilike('_changelog%'), Submission.author_id.in_(admins))

	if t != 'all':
		posts = apply_time_filter(posts, t, Submission)
	posts = sort_objects(posts, sort, Submission)

	posts = posts.offset(25 * (page - 1)).limit(26).all()

	return [x[0] for x in posts]


@app.get("/random_post")
@auth_desired
def random_post(v):

	p = g.db.query(Submission.id).filter(Submission.deleted_utc == 0, Submission.is_banned == False, Submission.private == False).order_by(func.random()).first()

	if p: p = p[0]
	else: abort(404)

	return redirect(f"/post/{p}")


@app.get("/random_user")
@auth_desired
def random_user(v):
	u = g.db.query(User.username).order_by(func.random()).first()
	
	if u: u = u[0]
	else: abort(404)

	return redirect(f"/@{u}")


@app.get("/comments")
@auth_required
def all_comments(v):
	page = max(request.values.get("page", 1, int), 1)
	sort = request.values.get("sort", "new")
	time_filter = request.values.get("t", defaulttimefilter)
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
	comments = sort_comment_results(comments, sort=sort)

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
			Comment.is_banned == False,
			Comment.deleted_utc == 0,
			Submission.private == False, # comment parent post not private
			User.shadowbanned == None, # comment author not shadowbanned
			Comment.filter_state.notin_(('filtered', 'removed')),
		)

	if gt: comments = comments.filter(Comment.created_utc > gt)
	if lt: comments = comments.filter(Comment.created_utc < lt)

	if not gt and not lt:
		comments = apply_time_filter(comments, t, Comment)
	comments = sort_objects(comments, sort, Comment)

	comments = comments.offset(25 * (page - 1)).limit(26).all()
	return [x[0] for x in comments]
