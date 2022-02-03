from files.helpers.wrappers import *
from files.helpers.get import *
from files.__main__ import app, cache, limiter
from files.classes.submission import Submission

defaulttimefilter = environ.get("DEFAULT_TIME_FILTER", "all").strip()

@app.post("/clear")
@auth_required
def clear(v):
	for n in v.notifications.filter_by(read=False).all():
		n.read = True
		g.db.add(n)
	g.db.commit()
	return {"message": "Notifications cleared!"}

@app.get("/unread")
@auth_required
def unread(v):
	listing = g.db.query(Comment).join(Notification.comment).filter(
		Notification.read == False,
		Notification.user_id == v.id,
		Comment.is_banned == False,
		Comment.deleted_utc == 0,
		Comment.author_id != AUTOJANNY_ID,
	).order_by(Notification.id.desc()).all()

	for n in v.notifications.filter_by(read=False).all():
		n.read = True
		g.db.add(n)
	g.db.commit()

	return {"data":[x.json for x in listing]}

@app.get("/notifications")
@auth_required
def notifications(v):
	try: page = int(request.values.get('page', 1))
	except: page = 1
	messages = request.values.get('messages')
	modmail = request.values.get('modmail')
	posts = request.values.get('posts')
	if modmail and v.admin_level > 1:
		comments = g.db.query(Comment).filter(Comment.sentto==0).order_by(Comment.id.desc()).offset(25*(page-1)).limit(26).all()
		next_exists = (len(comments) > 25)
		comments = comments[:25]
	elif messages:
		comments = g.db.query(Comment).filter(or_(Comment.author_id==v.id, Comment.sentto==v.id), Comment.parent_submission == None, not_(Comment.child_comments.any())).order_by(Comment.id.desc()).offset(25*(page-1)).limit(26).all()
		next_exists = (len(comments) > 25)
		comments = comments[:25]
	elif posts:
		notifications = g.db.query(Notification, Comment).join(Comment, Notification.comment_id == Comment.id).filter(Notification.user_id == v.id, Comment.author_id == AUTOJANNY_ID).order_by(Notification.id.desc()).offset(25 * (page - 1)).limit(101).all()

		for index, x in enumerate(notifications[:100]):
			if not x[0].read:
				x[0].read = True
				x[1].unread = True
				g.db.add(x[0])

		g.db.commit()

		listing = [x[1] for x in notifications][:25]
		next_exists = (len(notifications) > len(listing))

	else:
		notifications = g.db.query(Notification, Comment).join(Comment, Notification.comment_id == Comment.id).filter(
			Notification.user_id == v.id,
			Comment.is_banned == False,
			Comment.deleted_utc == 0,
			Comment.author_id != AUTOJANNY_ID,
		).order_by(Notification.id.desc()).offset(25 * (page - 1)).limit(26).all()

		next_exists = (len(notifications) > 25)
		notifications = notifications[:25]

		for x in notifications:
			if not x[0].read: x[1].unread = True
			x[0].read = True
			g.db.add(x[0])
	
		g.db.commit()
		
		comments = [x[1] for x in notifications]

	if not posts:
		listing = []
		all = set()
		for c in comments:
			c.is_blocked = False
			c.is_blocking = False
			if c.parent_submission and c.parent_comment and c.parent_comment.author_id == v.id:
				replies = []
				for x in c.replies:
					if x.author_id == v.id:
						x.voted = 1
						replies.append(x)
						all.add(x.id)
				c.replies = replies

				while c.parent_comment and (c.parent_comment.author_id == v.id or c.parent_comment in comments):
					parent = c.parent_comment
					if c not in parent.replies2:
						parent.replies2 = parent.replies2 + [c]
						all.add(c.id)
						parent.replies = parent.replies2
					c = parent

				if c not in listing:
					all.add(c.id)
					listing.append(c)
					c.replies = c.replies2
			elif c.parent_submission:
				replies = []
				for x in c.replies:
					if x.author_id == v.id:
						x.voted = 1
						replies.append(x)
						all.add(x.id)
				c.replies = replies
				if c not in listing:
					all.add(c.id)
					listing.append(c)
			else:
				if c.parent_comment:
					while c.level > 1:
						all.add(c.id)
						c = c.parent_comment

				if c not in listing:
					all.add(c.id)
					listing.append(c)

		all = all | set([x.id for x in comments]) | set([x.id for x in listing])
		comments = get_comments(all, v=v)

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
@app.get("/logged_out")
@limiter.limit("3/second;30/minute;400/hour;2000/day")
@auth_desired
def front_all(v):
	if not session.get("session_id"):
		session.permanent = True
		session["session_id"] = secrets.token_hex(49)

	if not v and request.path == "/" and not request.headers.get("Authorization"):
		return redirect(f"{SITE_FULL}/logged_out{request.full_path}")

	if v and request.path.startswith('/logged_out'): v = None

	try: page = max(int(request.values.get("page", 1)), 1)
	except: abort(400)

	if v:
		defaultsorting = v.defaultsorting
		defaulttime = v.defaulttime
	else:
		defaultsorting = "hot"
		defaulttime = defaulttimefilter

	sort=request.values.get("sort", defaultsorting)
	t=request.values.get('t', defaulttime)
	ccmode=request.values.get('ccmode', "false")

	ids, next_exists = frontlist(sort=sort,
					page=page,
					t=t,
					v=v,
					ccmode=ccmode,
					filter_words=v.filter_words if v else [],
					gt=int(request.values.get("utc_greater_than", 0)),
					lt=int(request.values.get("utc_less_than", 0)),
					)

	posts = get_posts(ids, v=v)
	
	if v and v.hidevotedon: posts = [x for x in posts if not hasattr(x, 'voted') or not x.voted]

	if request.headers.get("Authorization"): return {"data": [x.json for x in posts], "next_exists": next_exists}
	return render_template("home.html", v=v, listing=posts, next_exists=next_exists, sort=sort, t=t, page=page, ccmode=ccmode)



@cache.memoize(timeout=86400)
def frontlist(v=None, sort="hot", page=1, t="all", ids_only=True, ccmode="false", filter_words='', gt=None, lt=None):

	posts = g.db.query(Submission)

	if t == 'all': cutoff = 0
	else:
		now = int(time.time())
		if t == 'hour': cutoff = now - 3600
		elif t == 'week': cutoff = now - 604800
		elif t == 'month': cutoff = now - 2592000
		elif t == 'year': cutoff = now - 31536000
		else: cutoff = now - 86400
		posts = posts.filter(Submission.created_utc >= cutoff)

	if (ccmode == "true"):
		posts = posts.filter(Submission.club == True)

	if sort == "hot" or (v and v.id == Q_ID): posts = posts.filter_by(is_banned=False, stickied=None, private=False, deleted_utc = 0)
	else: posts = posts.filter_by(is_banned=False, private=False, deleted_utc = 0)

	if v and v.admin_level == 0:
		blocking = [x[0] for x in g.db.query(
			UserBlock.target_id).filter_by(
			user_id=v.id).all()]
		blocked = [x[0] for x in g.db.query(
			UserBlock.user_id).filter_by(
			target_id=v.id).all()]
		posts = posts.filter(
			Submission.author_id.notin_(blocking),
			Submission.author_id.notin_(blocked)
		)

	if not (v and v.changelogsub):
		posts=posts.filter(not_(Submission.title.ilike('[changelog]%')))

	if v and filter_words:
		for word in filter_words:
			posts=posts.filter(not_(Submission.title.ilike(f'%{word}%')))

	if gt: posts = posts.filter(Submission.created_utc > gt)
	if lt: posts = posts.filter(Submission.created_utc < lt)

	if not (v and v.shadowbanned):
		posts = posts.join(User, User.id == Submission.author_id).filter(User.shadowbanned == None)

	if sort == "hot":
		ti = int(time.time()) + 3600
		posts = posts.order_by(-1000000*(Submission.realupvotes + 1 + Submission.comment_count/5 + (func.length(Submission.body_html)-func.length(func.replace(Submission.body_html,'</a>','')))/4)/(func.power(((ti - Submission.created_utc)/1000), 1.23)))
	elif sort == "new":
		posts = posts.order_by(Submission.created_utc.desc())
	elif sort == "old":
		posts = posts.order_by(Submission.created_utc.asc())
	elif sort == "controversial":
		posts = posts.order_by(-1 * Submission.upvotes * Submission.downvotes * Submission.downvotes)
	elif sort == "top":
		posts = posts.order_by(Submission.downvotes - Submission.upvotes)
	elif sort == "bottom":
		posts = posts.order_by(Submission.upvotes - Submission.downvotes)
	elif sort == "comments":
		posts = posts.order_by(Submission.comment_count.desc())

	if v: size = v.frontsize or 0
	else: size = 25

	posts = posts.offset(size * (page - 1)).limit(size+1).all()

	next_exists = (len(posts) > size)

	posts = posts[:size]

	if (sort == "hot" or (v and v.id == Q_ID)) and page == 1 and ccmode == "false":
		pins = g.db.query(Submission).filter(Submission.stickied != None, Submission.is_banned == False)
		if v and v.admin_level == 0:
			blocking = [x[0] for x in g.db.query(UserBlock.target_id).filter_by(user_id=v.id).all()]
			blocked = [x[0] for x in g.db.query(UserBlock.user_id).filter_by(target_id=v.id).all()]
			pins = pins.filter(Submission.author_id.notin_(blocking), Submission.author_id.notin_(blocked))

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


	page = int(request.values.get("page") or 1)
	page = max(page, 1)

	sort=request.values.get("sort", "new")
	t=request.values.get('t', "all")

	ids = changeloglist(sort=sort,
					page=page,
					t=t,
					v=v,
					)

	next_exists = (len(ids) > 25)
	ids = ids[:25]

	posts = get_posts(ids, v=v)

	if request.headers.get("Authorization"): return {"data": [x.json for x in posts], "next_exists": next_exists}
	return render_template("changelog.html", v=v, listing=posts, next_exists=next_exists, sort=sort, t=t, page=page)


@cache.memoize(timeout=86400)
def changeloglist(v=None, sort="new", page=1 ,t="all"):

	posts = g.db.query(Submission.id).filter_by(is_banned=False, private=False,).filter(Submission.deleted_utc == 0)

	if v and v.admin_level == 0:
		blocking = [x[0] for x in g.db.query(
			UserBlock.target_id).filter_by(
			user_id=v.id).all()]
		blocked = [x[0] for x in g.db.query(
			UserBlock.user_id).filter_by(
			target_id=v.id).all()]
		posts = posts.filter(
			Submission.author_id.notin_(blocking),
			Submission.author_id.notin_(blocked)
		)

	admins = [x[0] for x in g.db.query(User.id).filter(User.admin_level > 1).all()]
	posts = posts.filter(Submission.title.ilike('_changelog%'), Submission.author_id.in_(admins))

	if t != 'all':
		cutoff = 0
		now = int(time.time())
		if t == 'hour':
			cutoff = now - 3600
		elif t == 'day':
			cutoff = now - 86400
		elif t == 'week':
			cutoff = now - 604800
		elif t == 'month':
			cutoff = now - 2592000
		elif t == 'year':
			cutoff = now - 31536000
		posts = posts.filter(Submission.created_utc >= cutoff)

	if sort == "new":
		posts = posts.order_by(Submission.created_utc.desc())
	elif sort == "old":
		posts = posts.order_by(Submission.created_utc.asc())
	elif sort == "controversial":
		posts = posts.order_by(-1 * Submission.upvotes * Submission.downvotes * Submission.downvotes)
	elif sort == "top":
		posts = posts.order_by(Submission.downvotes - Submission.upvotes)
	elif sort == "bottom":
		posts = posts.order_by(Submission.upvotes - Submission.downvotes)
	elif sort == "comments":
		posts = posts.order_by(Submission.comment_count.desc())

	posts = posts.offset(25 * (page - 1)).limit(26).all()

	return [x[0] for x in posts]


@app.get("/random")
@auth_required
def random_post(v):

	x = g.db.query(Submission).filter(Submission.deleted_utc == 0, Submission.is_banned == False)
	total = x.count()
	n = random.randint(1, total - 2)

	post = x.offset(n).limit(1).one_or_none()
	return redirect(f"{SITE_FULL}/post/{post.id}")

@cache.memoize(timeout=86400)
def comment_idlist(page=1, v=None, nsfw=False, sort="new", t="all"):

	cc_idlist = [x[0] for x in g.db.query(Submission.id).filter(Submission.club == True).all()]

	comments = g.db.query(Comment.id).filter(Comment.parent_submission.notin_(cc_idlist))

	if v and v.admin_level <= 3:
		blocking = [x[0] for x in g.db.query(
			UserBlock.target_id).filter_by(
			user_id=v.id).all()]
		blocked = [x[0] for x in g.db.query(
			UserBlock.user_id).filter_by(
			target_id=v.id).all()]

		comments = comments.filter(Comment.author_id.notin_(blocking), Comment.author_id.notin_(blocked))

	if not v or not v.admin_level > 1:
		comments = comments.filter(Comment.is_banned==False, Comment.deleted_utc == 0)

	now = int(time.time())
	if t == 'hour':
		cutoff = now - 3600
	elif t == 'day':
		cutoff = now - 86400
	elif t == 'week':
		cutoff = now - 604800
	elif t == 'month':
		cutoff = now - 2592000
	elif t == 'year':
		cutoff = now - 31536000
	else:
		cutoff = 0
	comments = comments.filter(Comment.created_utc >= cutoff)

	if sort == "new":
		comments = comments.order_by(Comment.created_utc.desc())
	elif sort == "old":
		comments = comments.order_by(Comment.created_utc.asc())
	elif sort == "controversial":
		comments = comments.order_by(-1 * Comment.upvotes * Comment.downvotes * Comment.downvotes)
	elif sort == "top":
		comments = comments.order_by(Comment.downvotes - Comment.upvotes)
	elif sort == "bottom":
		comments = comments.order_by(Comment.upvotes - Comment.downvotes)

	comments = comments.offset(25 * (page - 1)).limit(26).all()
	return [x[0] for x in comments]

@app.get("/comments")
@auth_required
def all_comments(v):


	page = int(request.values.get("page", 1))

	sort=request.values.get("sort", "new")
	t=request.values.get("t", defaulttimefilter)

	idlist = comment_idlist(v=v,
							page=page,
							sort=sort,
							t=t,
							)

	comments = get_comments(idlist, v=v)

	next_exists = len(idlist) > 25

	idlist = idlist[:25]

	if request.headers.get("Authorization"): return {"data": [x.json for x in comments]}
	return render_template("home_comments.html", v=v, sort=sort, t=t, page=page, comments=comments, standalone=True, next_exists=next_exists)


@app.get("/transfers")
@auth_required
def transfers(v):

	comments = g.db.query(Comment).filter(Comment.author_id == NOTIFICATIONS_ID, Comment.parent_submission == None, Comment.distinguish_level == 6, Comment.body_html.like("%</a> has transferred %"), Comment.created_utc == 0).order_by(Comment.id.desc())

	if request.headers.get("Authorization"): return {"data": [x.json for x in comments.all()]}

	page = int(request.values.get("page", 1))
	comments = comments.offset(25 * (page - 1)).limit(26).all()
	next_exists = len(comments) > 25
	comments = comments[:25]
	return render_template("transfers.html", v=v, page=page, comments=comments, standalone=True, next_exists=next_exists)