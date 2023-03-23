import time
import urllib.parse
from io import BytesIO
from os import path
from sys import stdout
from urllib.parse import ParseResult, urlparse

import gevent
import requests
import werkzeug.wrappers
from PIL import Image as PILimage
from sqlalchemy.orm import Query

import files.helpers.validators as validators
from files.__main__ import app, cache, db_session, limiter
from files.classes import *
from files.helpers.alerts import *
from files.helpers.caching import invalidate_cache
from files.helpers.comments import comment_filter_moderated
from files.helpers.config.const import *
from files.helpers.content import canonicalize_url2
from files.helpers.contentsorting import sort_objects
from files.helpers.media import process_image
from files.helpers.sanitize import *
from files.helpers.strings import sql_ilike_clean
from files.helpers.wrappers import *
from files.routes.importstar import *


discounts = { # <- why is this here?
	69: 0.02,
	70: 0.04,
	71: 0.06,
	72: 0.08,
	73: 0.10,
}

titleheaders = {
	"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.72 Safari/537.36"
}

MAX_TITLE_LENGTH = 500
MAX_URL_LENGTH = 2048


@app.post("/toggle_club/<pid>")
@auth_required
def toggle_club(pid, v):

	post = get_post(pid)
	if post.author_id != v.id and v.admin_level < 2: abort(403)

	post.club = not post.club
	g.db.add(post)

	g.db.commit()

	if post.club: return {"message": "Post has been marked as club-only!"}
	else: return {"message": "Post has been unmarked as club-only!"}


@app.post("/publish/<pid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def publish(pid, v):
	post = get_post(pid)
	if not post.private: return {"message": "Post published!"}

	if post.author_id != v.id: abort(403)
	post.private = False
	post.created_utc = int(time.time())
	g.db.add(post)
	
	post.publish()
	g.db.commit()
	return redirect(post.permalink)

@app.get("/submit")
# @app.get("/h/<sub>/submit")
@auth_required
def submit_get(v, sub=None):
	if sub: sub = g.db.query(Sub.name).filter_by(name=sub.strip().lower()).one_or_none()
	
	if request.path.startswith('/h/') and not sub: abort(404)

	SUBS = [x[0] for x in g.db.query(Sub.name).order_by(Sub.name).all()]

	return render_template("submit.html", SUBS=SUBS, v=v, sub=sub)

@app.get("/post/<pid>")
@app.get("/post/<pid>/<anything>")
# @app.get("/h/<sub>/post/<pid>")
# @app.get("/h/<sub>/post/<pid>/<anything>")
@auth_desired
def post_id(pid, anything=None, v=None, sub=None):
	post = get_post(pid, v=v)

	if post.over_18 and not (v and v.over_18) and session.get('over_18', 0) < int(time.time()):
		if request.headers.get("Authorization") or request.headers.get("xhr"): abort(403, "Must be 18+ to view")
		return render_template("errors/nsfw.html", v=v)

	if v: defaultsortingcomments = v.defaultsortingcomments
	else: defaultsortingcomments = "new"
	sort = request.values.get("sort", defaultsortingcomments)

	if post.club and not (v and (v.paid_dues or v.id == post.author_id)): abort(403)

	limit = app.config['RESULTS_PER_PAGE_COMMENTS']
	offset = 0

	top_comments = g.db.query(Comment.id, Comment.descendant_count).filter(
		Comment.parent_submission == post.id,
		Comment.level == 1,
	).order_by(Comment.is_pinned.desc().nulls_last())
	top_comments = comment_filter_moderated(top_comments, v)
	top_comments = sort_objects(top_comments, sort, Comment)

	pg_top_comment_ids = []
	pg_comment_qty = 0
	for tc_id, tc_children_qty in top_comments.all():
		if pg_comment_qty >= limit:
			offset = 1
			break
		pg_comment_qty += tc_children_qty + 1
		pg_top_comment_ids.append(tc_id)

	def comment_tree_filter(q: Query) -> Query:
		q = q.filter(Comment.top_comment_id.in_(pg_top_comment_ids))
		q = comment_filter_moderated(q, v)
		return q

	comments, comment_tree = get_comment_trees_eager(comment_tree_filter, sort, v)
	post.replies = comment_tree[None] # parent=None -> top-level comments
	ids = {c.id for c in post.replies}

	post.views += 1
	g.db.expire_on_commit = False
	g.db.add(post)
	g.db.commit()
	g.db.expire_on_commit = True

	if request.headers.get("Authorization"): return post.json
	else:
		if post.is_banned and not (v and (v.admin_level > 1 or post.author_id == v.id)): template = "submission_banned.html"
		else: template = "submission.html"
		return render_template(template, v=v, p=post, ids=list(ids), sort=sort, render_replies=True, offset=offset, sub=post.subr)

@app.get("/viewmore/<pid>/<sort>/<offset>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_desired
def viewmore(v, pid, sort, offset):
	post = get_post(pid, v=v)
	if post.club and not (v and (v.paid_dues or v.id == post.author_id)): abort(403)

	offset_prev = int(offset)
	try: ids = set(int(x) for x in request.values.get("ids").split(','))
	except: abort(400)
	
	limit = app.config['RESULTS_PER_PAGE_COMMENTS']
	offset = 0

	# TODO: Unify with common post_id logic
	top_comments = g.db.query(Comment.id, Comment.descendant_count).filter(
		Comment.parent_submission == post.id,
		Comment.level == 1,
		Comment.id.notin_(ids),
		Comment.is_pinned == None,
	).order_by(Comment.is_pinned.desc().nulls_last())

	if sort == "new":
		newest_created_utc = g.db.query(Comment.created_utc).filter(
			Comment.id.in_(ids),
			Comment.is_pinned == None,
		).order_by(Comment.created_utc.desc()).limit(1).scalar()

		# Needs to be <=, not just <, to support seed_db data which has many identical
		# created_utc values. Shouldn't cause duplication in real data because of the
		# `NOT IN :ids` in top_comments.
		top_comments = top_comments.filter(Comment.created_utc <= newest_created_utc)

	top_comments = comment_filter_moderated(top_comments, v)
	top_comments = sort_objects(top_comments, sort, Comment)

	pg_top_comment_ids = []
	pg_comment_qty = 0
	for tc_id, tc_children_qty in top_comments.all():
		if pg_comment_qty >= limit:
			offset = offset_prev + 1
			break
		pg_comment_qty += tc_children_qty + 1
		pg_top_comment_ids.append(tc_id)

	def comment_tree_filter(q: Query) -> Query:
		q = q.filter(Comment.top_comment_id.in_(pg_top_comment_ids))
		q = comment_filter_moderated(q, v)
		return q

	_, comment_tree = get_comment_trees_eager(comment_tree_filter, sort, v)
	comments = comment_tree[None] # parent=None -> top-level comments
	ids |= {c.id for c in comments}

	return render_template("comments.html", v=v, comments=comments, p=post, ids=list(ids), render_replies=True, pid=pid, sort=sort, offset=offset, ajax=True)


@app.get("/morecomments/<cid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_desired
def morecomments(v, cid):
	try: cid = int(cid)
	except: abort(400)

	tcid = g.db.query(Comment.top_comment_id).filter_by(id=cid).one_or_none()[0]

	if v:
		votes = g.db.query(CommentVote).filter_by(user_id=v.id).subquery()

		blocking = v.blocking.subquery()

		blocked = v.blocked.subquery()

		comments = g.db.query(
			Comment,
			votes.c.vote_type,
			blocking.c.target_id,
			blocked.c.target_id,
		).filter(Comment.top_comment_id == tcid, Comment.level > RENDER_DEPTH_LIMIT).join(
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
		dump = []
		for c in comments.all():
			comment = c[0]
			comment.voted = c[1] or 0
			comment.is_blocking = c[2] or 0
			comment.is_blocked = c[3] or 0
			if c[0].parent_comment_id == int(cid): output.append(comment)
			else: dump.append(comment)
		comments = output
	else:
		c = g.db.query(Comment).filter_by(id=cid).one_or_none()
		comments = c.replies(None)

	if comments: p = comments[0].post
	else: p = None
	
	return render_template("comments.html", v=v, comments=comments, p=p, render_replies=True, ajax=True)


@app.post("/edit_post/<int:pid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def edit_post(pid, v):
	p = get_post(pid)
	if not v.can_edit(p): abort(403)

	validated_post: validators.ValidatedSubmissionLike = \
		validators.ValidatedSubmissionLike.from_flask_request(
			request,
			allow_embedding=MULTIMEDIA_EMBEDDING_ENABLED,
			allow_media_url_upload=False,
			embed_url_file_key="file",
			edit=True
		)
	changed:bool=False

	if validated_post.title != p.title:
		p.title = validated_post.title
		p.title_html = validated_post.title_html
		changed = True

	if validated_post.body != validated_post.body:
		p.body = validated_post.body
		p.body_html = validated_post.body_html
		changed = True

	if not changed:
		abort(400, "You need to change something")

	p.publish()

	if v.id == p.author_id:
		if int(time.time()) - p.created_utc > 60 * 3: p.edited_utc = int(time.time())
		g.db.add(p)
	else:
		ma=ModAction(
			kind="edit_post",
			user_id=v.id,
			target_submission_id=p.id
		)
		g.db.add(ma)

	g.db.commit()

	return redirect(p.permalink)


def archiveorg(url):
	try: requests.get(f'https://web.archive.org/save/{url}', headers={'User-Agent': 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'}, timeout=100)
	except: pass


def thumbnail_thread(pid):
	db = db_session()

	def expand_url(post_url, fragment_url):
		if fragment_url.startswith("https://"):
			return fragment_url
		elif fragment_url.startswith("https://"):
			return f"https://{fragment_url.split('https://')[1]}"
		elif fragment_url.startswith('//'):
			return f"https:{fragment_url}"
		elif fragment_url.startswith('/'):
			parsed_url = urlparse(post_url)
			return f"https://{parsed_url.netloc}{fragment_url}"
		else:
			return f"{post_url}{'/' if not post_url.endswith('/') else ''}{fragment_url}"

	post = db.query(Submission).filter_by(id=pid).one_or_none()
	
	if not post or not post.url:
		time.sleep(5)
		post = db.query(Submission).filter_by(id=pid).one_or_none()

	if not post or not post.url: return
	
	fetch_url = post.url

	if fetch_url.startswith('/'): fetch_url = f"{SITE_FULL}{fetch_url}"

	headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.72 Safari/537.36"}

	try:
		x=requests.get(fetch_url, headers=headers, timeout=5, proxies=proxies)
	except:
		db.close()
		return

	if x.status_code != 200:
		db.close()
		return

	if x.headers.get("Content-Type","").startswith("text/html"):
		soup=BeautifulSoup(x.content, 'lxml')

		thumb_candidate_urls=[]

		meta_tags = [
			"themotte:thumbnail",
			"twitter:image",
			"og:image",
			"thumbnail"
			]

		for tag_name in meta_tags:
			tag = soup.find(
				'meta', 
				attrs={
					"name": tag_name, 
					"content": True
					}
				)
			if not tag:
				tag = soup.find(
					'meta',
					attrs={
						'property': tag_name,
						'content': True
						}
					)
			if tag:
				thumb_candidate_urls.append(expand_url(post.url, tag['content']))

		for tag in soup.find_all("img", attrs={'src':True}):
			thumb_candidate_urls.append(expand_url(post.url, tag['src']))


		for url in thumb_candidate_urls:

			try:
				image_req=requests.get(url, headers=headers, timeout=5, proxies=proxies)
			except:
				continue

			if image_req.status_code >= 400:
				continue

			if not image_req.headers.get("Content-Type","").startswith("image/"):
				continue

			if image_req.headers.get("Content-Type","").startswith("image/svg"):
				continue

			image = PILimage.open(BytesIO(image_req.content))
			if image.width < 30 or image.height < 30:
				continue

			break

		else:
			db.close()
			return



	elif x.headers.get("Content-Type","").startswith("image/"):
		image_req=x
		image = PILimage.open(BytesIO(x.content))

	else:
		db.close()
		return

	size = len(image.fp.read())
	if size > 8 * 1024 * 1024:
		db.close()
		return

	name = f'/images/{time.time()}'.replace('.','') + '.webp'

	with open(name, "wb") as file:
		for chunk in image_req.iter_content(1024):
			file.write(chunk)

	post.thumburl = process_image(name, resize=100)
	db.add(post)
	db.commit()

	db.commit()
	db.close()
	stdout.flush()
	return


@app.post("/is_repost")
def api_is_repost():
	url = request.values.get('url')
	if not url: abort(400)

	url = urllib.parse.unparse(canonicalize_url2(url, httpsify=True))
	if url.endswith('/'): url = url[:-1]

	search_url = sql_ilike_clean(url)
	repost = g.db.query(Submission).filter(
		Submission.url.ilike(search_url),
		Submission.deleted_utc == 0,
		Submission.is_banned == False
	).first()
	if repost: return {'permalink': repost.permalink}
	else: return {'permalink': ''}


def _do_antispam_submission_check(v:User, validated:validators.ValidatedSubmissionLike):
	now = int(time.time())
	cutoff = now - 60 * 60 * 24

	similar_posts = g.db.query(Submission).filter(
		Submission.author_id == v.id,
		Submission.title.op('<->')(validated.title) < app.config["SPAM_SIMILARITY_THRESHOLD"],
		Submission.created_utc > cutoff
	).all()

	if validated.url:
		similar_urls = g.db.query(Submission).filter(
			Submission.author_id == v.id,
			Submission.url.op('<->')(validated.url) < app.config["SPAM_URL_SIMILARITY_THRESHOLD"],
			Submission.created_utc > cutoff
		).all()
	else: 
		similar_urls = []

	threshold = app.config["SPAM_SIMILAR_COUNT_THRESHOLD"]
	if v.age_seconds >= (60 * 60 * 24 * 7): threshold *= 3
	elif v.age_seconds >= (60 * 60 * 24): threshold *= 2

	if max(len(similar_urls), len(similar_posts)) < threshold:
		return

	text = "Your account has been banned for **1 day** for the following reason:\n\n> Too much spam!"
	send_repeatable_notification(v.id, text)

	v.ban(reason="Spamming.", days=1)
	for post in similar_posts + similar_urls:
		post.is_banned = True
		post.is_pinned = False
		post.ban_reason = "AutoJanny"
		g.db.add(post)
		ma=ModAction(
				user_id=AUTOJANNY_ID,
				target_submission_id=post.id,
				kind="ban_post",
				_note="spam"
		)
		g.db.add(ma)
	g.db.commit()
	abort(403)


def _execute_domain_ban_check(parsed_url:ParseResult):
	domain:str = parsed_url.netloc
	domain_obj = get_domain(domain)
	if not domain_obj: 
		domain_obj = get_domain(domain+parsed_url.path)
	if not domain_obj: return
	abort(403, f"Remove the {domain_obj.domain} link from your post and try again. {domain_obj.reason}")


def _duplicate_check(search_url:Optional[str]) -> Optional[werkzeug.wrappers.Response]:
	if not search_url: return None
	repost = g.db.query(Submission).filter(
		func.lower(Submission.url) == search_url.lower(),
		Submission.deleted_utc == 0,
		Submission.is_banned == False
	).first()
	if repost and SITE != 'localhost': 
		return redirect(repost.permalink)
	return None


def _duplicate_check2(
		user_id:int, 
		validated_post:validators.ValidatedSubmissionLike) -> Optional[werkzeug.wrappers.Response]:
	dup = g.db.query(Submission).filter(
		Submission.author_id == user_id,
		Submission.deleted_utc == 0,
		Submission.title == validated_post.title,
		Submission.url == validated_post.url,
		Submission.body == validated_post.body
	).one_or_none()

	if dup and SITE != 'localhost': 
		return redirect(dup.permalink)
	return None


@app.post("/submit")
# @app.post("/h/<sub>/submit")
@limiter.limit("1/second;2/minute;10/hour;50/day")
@auth_required
def submit_post(v, sub=None):
	def error(error):
		title:str = request.values.get("title", "")
		body:str = request.values.get("body", "")
		url:str = request.values.get("url", "")

		if request.headers.get("Authorization") or request.headers.get("xhr"): abort(400, error)
	
		SUBS = [x[0] for x in g.db.query(Sub.name).order_by(Sub.name).all()]
		return render_template("submit.html", SUBS=SUBS, v=v, error=error, title=title, url=url, body=body), 400

	if v.is_suspended: return error("You can't perform this action while banned.")

	try:
		validated_post: validators.ValidatedSubmissionLike = \
			validators.ValidatedSubmissionLike.from_flask_request(request,
				allow_embedding=MULTIMEDIA_EMBEDDING_ENABLED,
			)
	except ValueError as e:
		return error(str(e))

	sub = request.values.get("sub")
	if sub: sub = sub.replace('/h/','').replace('s/','')

	if sub and sub != 'none':
		sname = sub.strip().lower()
		sub = g.db.query(Sub.name).filter_by(name=sname).one_or_none()
		if not sub: return error(f"/h/{sname} not found!")
		sub = sub[0]
		if v.exiled_from(sub): return error(f"You're exiled from /h/{sub}")
	else: sub = None

	duplicate:Optional[werkzeug.wrappers.Response] = \
		_duplicate_check(validated_post.repost_search_url)
	if duplicate: return duplicate

	parsed_url:Optional[ParseResult] = validated_post.url_canonical
	if parsed_url:
		_execute_domain_ban_check(parsed_url)

	duplicate:Optional[werkzeug.wrappers.Response] = \
		_duplicate_check2(v.id, validated_post)
	if duplicate: return duplicate

	_do_antispam_submission_check(v, validated_post)

	club = bool(request.values.get("club",""))
	is_bot = bool(request.headers.get("Authorization"))

	# Invariant: these values are guarded and obey the length bound
	assert len(validated_post.title) <= MAX_TITLE_LENGTH
	assert len(validated_post.body) <= SUBMISSION_BODY_LENGTH_MAXIMUM

	post = Submission(
		private=bool(request.values.get("private","")),
		club=club,
		author_id=v.id,
		over_18=bool(request.values.get("over_18","")),
		app_id=v.client.application.id if v.client else None,
		is_bot=is_bot,
		url=validated_post.url,
		body=validated_post.body,
		body_html=validated_post.body_html,
		embed_url=validated_post.embed_slow,
		title=validated_post.title,
		title_html=validated_post.title_html,
		sub=sub,
		ghost=False,
		filter_state='filtered' if v.admin_level == 0 and app.config['SETTINGS']['FilterNewPosts'] else 'normal',
		thumburl=validated_post.thumburl
	)
	post.submit(g.db)
		
	if not post.thumburl and post.url:
		gevent.spawn(thumbnail_thread, post.id)

	post.publish()
	g.db.commit()

	if request.headers.get("Authorization"): 
		return post.json
	else:
		post.voted = 1
		if 'megathread' in post.title.lower(): sort = 'new'
		else: sort = v.defaultsortingcomments
		return render_template('submission.html', v=v, p=post, sort=sort, render_replies=True, offset=0, success=True, sub=post.subr)


@app.post("/delete_post/<pid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def delete_post_pid(pid, v):
	post = get_post(pid)
	if post.author_id != v.id:
		abort(403)

	post.deleted_utc = int(time.time())
	post.is_pinned = False
	post.stickied = None

	g.db.add(post)

	invalidate_cache()

	g.db.commit()

	return {"message": "Post deleted!"}

@app.post("/undelete_post/<pid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def undelete_post_pid(pid, v):
	post = get_post(pid)
	if post.author_id != v.id: abort(403)
	post.deleted_utc = 0

	g.db.add(post)

	invalidate_cache()

	g.db.commit()

	return {"message": "Post undeleted!"}


@app.post("/toggle_comment_nsfw/<cid>")
@auth_required
def toggle_comment_nsfw(cid, v):

	comment = g.db.query(Comment).filter_by(id=cid).one_or_none()
	if comment.author_id != v.id and not v.admin_level > 1: abort(403)
	comment.over_18 = not comment.over_18
	g.db.add(comment)

	g.db.commit()

	if comment.over_18: return {"message": "Comment has been marked as +18!"}
	else: return {"message": "Comment has been unmarked as +18!"}
	
@app.post("/toggle_post_nsfw/<pid>")
@auth_required
def toggle_post_nsfw(pid, v):

	post = get_post(pid)

	if post.author_id != v.id and not v.admin_level > 1:
		abort(403)

	post.over_18 = not post.over_18
	g.db.add(post)

	if post.author_id!=v.id:
		ma=ModAction(
			kind="set_nsfw" if post.over_18 else "unset_nsfw",
			user_id=v.id,
			target_submission_id=post.id,
			)
		g.db.add(ma)

	g.db.commit()

	if post.over_18: return {"message": "Post has been marked as +18!"}
	else: return {"message": "Post has been unmarked as +18!"}

@app.post("/save_post/<pid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def save_post(pid, v):

	post=get_post(pid)

	save = g.db.query(SaveRelationship).filter_by(user_id=v.id, submission_id=post.id).one_or_none()

	if not save:
		new_save=SaveRelationship(user_id=v.id, submission_id=post.id)
		g.db.add(new_save)
		g.db.commit()

	return {"message": "Post saved!"}

@app.post("/unsave_post/<pid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def unsave_post(pid, v):

	post=get_post(pid)

	save = g.db.query(SaveRelationship).filter_by(user_id=v.id, submission_id=post.id).one_or_none()

	if save:
		g.db.delete(save)
		g.db.commit()

	return {"message": "Post unsaved!"}

@app.post("/pin/<post_id>")
@auth_required
def api_pin_post(post_id, v):
	post = get_post(post_id)
	if v.id != post.author_id: abort(403, "Only the post author's can do that!")
	post.is_pinned = not post.is_pinned
	g.db.add(post)

	cache.delete_memoized(User.userpagelisting)

	g.db.commit()
	if post.is_pinned: return {"message": "Post pinned!"}
	else: return {"message": "Post unpinned!"}

@app.get("/submit/title")
@limiter.limit("6/minute")
@auth_required
def get_post_title(v):
	POST_TITLE_TIMEOUT = 5
	url = request.values.get("url")
	if not url or '\\' in url: abort(400)
	url = url.strip()
	if not url.startswith('http'): abort(400)
	checking_url = url.lower().split('?')[0].split('%3F')[0]
	if any((checking_url.endswith(f'.{x}') for x in NO_TITLE_EXTENSIONS)):
		abort(400)

	try:
		x = gevent.with_timeout(POST_TITLE_TIMEOUT, requests.get, 
			                    url, headers=titleheaders, timeout=POST_TITLE_TIMEOUT, 
							    proxies=proxies)
	except: abort(400)
		
	content_type = x.headers.get("Content-Type")
	if not content_type or "text/html" not in content_type: abort(400)

	match = html_title_regex.search(x.text)
	if match and match.lastindex >= 1:
		title = html.unescape(match.group(1))
	else: abort(400)

	return {"url": url, "title": title}
