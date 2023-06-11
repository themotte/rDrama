from sqlalchemy import *

from files.__main__ import app
from files.helpers.contentsorting import apply_time_filter, sort_objects
from files.helpers.strings import sql_ilike_clean
from files.helpers.wrappers import *
from files.routes.importstar import *

valid_params=[
	'author',
	'domain',
	'over18'
]

def searchparse(text):
	criteria = {x[0]:x[1] for x in query_regex.findall(text)}

	for x in criteria:
		if x in valid_params:
			text = text.replace(f"{x}:{criteria[x]}", "")

	text=text.strip()

	if text:
		criteria['q']=text

	return criteria


@app.get("/search/posts")
@auth_desired
def searchposts(v):
	query = request.values.get("q", '').strip()

	page = max(1, int(request.values.get("page", 1)))

	sort = request.values.get("sort", "new").lower()
	t = request.values.get('t', 'all').lower()

	criteria=searchparse(query)

	posts = g.db.query(Submission.id)
	
	if not (v and v.paid_dues): posts = posts.filter_by(club=False)
	
	if v and v.admin_level < 2:
		posts = posts.filter(Submission.state_user_deleted_utc == None, Submission.is_banned == False, Submission.private == False, Submission.author_id.notin_(v.userblocks))
	elif not v:
		posts = posts.filter(Submission.state_user_deleted_utc == None, Submission.is_banned == False, Submission.private == False)
	

	if 'author' in criteria:
		posts = posts.filter(Submission.ghost == False)
		author = get_user(criteria['author'])
		if author.is_private and (not v or (author.id != v.id and v.admin_level < 2)):
			if request.headers.get("Authorization"):
				abort(403, f"@{author.username}'s profile is private; You can't use the 'author' syntax on them")
			return render_template("search.html",
								v=v,
								query=query,
								total=0,
								page=page,
								listing=[],
								sort=sort,
								t=t,
								next_exists=False,
								domain=None,
								domain_obj=None,
								error=f"@{author.username}'s profile is private; You can't use the 'author' syntax on them."
								)
		else: posts = posts.filter(Submission.author_id == author.id)

	if 'q' in criteria:
		words = sql_ilike_clean(criteria['q']).split()
		words=[Submission.title.ilike('%'+x+'%') for x in words]
		posts=posts.filter(*words)
		
	if 'over18' in criteria: posts = posts.filter(Submission.over_18==True)

	if 'domain' in criteria:
		domain=criteria['domain']

		domain = sql_ilike_clean(domain)

		posts=posts.filter(
			or_(
				Submission.url.ilike("https://"+domain+'/%'),
				Submission.url.ilike("https://"+domain+'/%'),
				Submission.url.ilike("https://"+domain),
				Submission.url.ilike("https://"+domain),
				Submission.url.ilike("https://www."+domain+'/%'),
				Submission.url.ilike("https://www."+domain+'/%'),
				Submission.url.ilike("https://www."+domain),
				Submission.url.ilike("https://www."+domain),
				Submission.url.ilike("https://old." + domain + '/%'),
				Submission.url.ilike("https://old." + domain + '/%'),
				Submission.url.ilike("https://old." + domain),
				Submission.url.ilike("https://old." + domain)
				)
			)

	if t:
		posts = apply_time_filter(posts, t, Submission)
	posts = sort_objects(posts, sort, Submission)

	total = posts.count()

	posts = posts.offset(25 * (page - 1)).limit(26).all()

	ids = [x[0] for x in posts]


	next_exists = (len(ids) > 25)
	ids = ids[:25]

	posts = get_posts(ids, v=v, eager=True)

	if request.headers.get("Authorization"): return {"total":total, "data":[x.json for x in posts]}

	return render_template("search.html",
						   v=v,
						   query=query,
						   total=total,
						   page=page,
						   listing=posts,
						   sort=sort,
						   t=t,
						   next_exists=next_exists
						   )


@app.get("/search/comments")
@auth_desired
def searchcomments(v):
	query = request.values.get("q", '').strip()

	try: page = max(1, int(request.values.get("page", 1)))
	except: page = 1

	sort = request.values.get("sort", "new").lower()
	t = request.values.get('t', 'all').lower()

	criteria = searchparse(query)

	comments = g.db.query(Comment.id).filter(Comment.parent_submission != None)

	if 'author' in criteria:
		comments = comments.filter(Comment.ghost == False)
		author = get_user(criteria['author'])
		if author.is_private and (not v or (author.id != v.id and v.admin_level < 2)):
			if request.headers.get("Authorization"):
				abort(403, f"@{author.username}'s profile is private; You can't use the 'author' syntax on them")

			return render_template("search_comments.html", v=v, query=query, total=0, page=page, comments=[], sort=sort, t=t, next_exists=False, error=f"@{author.username}'s profile is private; You can't use the 'author' syntax on them.")

		else: comments = comments.filter(Comment.author_id == author.id)

	if 'q' in criteria:
		words = sql_ilike_clean(criteria['q']).split()

		words = [Comment.body.ilike('%'+x+'%') for x in words]
		comments = comments.filter(*words)

	if 'over18' in criteria: comments = comments.filter(Comment.over_18 == True)

	if t:
		comments = apply_time_filter(comments, t, Comment)

	if v and v.admin_level < 2:
		private = [x[0] for x in g.db.query(Submission.id).filter(Submission.private == True).all()]
		comments = comments.filter(Comment.author_id.notin_(v.userblocks), Comment.is_banned==False, Comment.state_user_deleted_utc == None, Comment.parent_submission.notin_(private))
	elif not v:
		private = [x[0] for x in g.db.query(Submission.id).filter(Submission.private == True).all()]
		comments = comments.filter(Comment.is_banned==False, Comment.state_user_deleted_utc == None, Comment.parent_submission.notin_(private))


	if not (v and v.paid_dues):
		club = [x[0] for x in g.db.query(Submission.id).filter(Submission.club == True).all()]
		comments = comments.filter(Comment.parent_submission.notin_(club))

	comments = sort_objects(comments, sort, Comment)

	total = comments.count()

	comments = comments.offset(25 * (page - 1)).limit(26).all()

	ids = [x[0] for x in comments]

	next_exists = (len(ids) > 25)
	ids = ids[:25]

	comments = get_comments(ids, v=v)

	if request.headers.get("Authorization"): return {"total":total, "data":[x.json for x in comments]}
	return render_template("search_comments.html", v=v, query=query, total=total, page=page, comments=comments, sort=sort, t=t, next_exists=next_exists, standalone=True)


@app.get("/search/users")
@auth_desired
def searchusers(v):
	query = request.values.get("q", '').strip()

	page = max(1, int(request.values.get("page", 1)))
	sort = request.values.get("sort", "new").lower()
	t = request.values.get('t', 'all').lower()
	term=query.lstrip('@')
	term = sql_ilike_clean(term)
	
	users=g.db.query(User).filter(User.username.ilike(f'%{term}%'))
	
	users=users.order_by(User.username.ilike(term).desc(), User.stored_subscriber_count.desc())
	
	total=users.count()
	
	users=[x for x in users.offset(25 * (page-1)).limit(26)]
	next_exists=(len(users)>25)
	users=users[:25]

	if request.headers.get("Authorization"): return {"data": [x.json for x in users]}
	return render_template("search_users.html", v=v, query=query, total=total, page=page, users=users, sort=sort, t=t, next_exists=next_exists)
