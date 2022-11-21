import time
import gevent
from files.helpers.wrappers import *
from files.helpers.sanitize import *
from files.helpers.strings import sql_ilike_clean
from files.helpers.alerts import *
from files.helpers.const import *
from files.classes import *
from flask import *
from io import BytesIO
from files.__main__ import app, limiter, cache, db_session
from PIL import Image as PILimage
from .front import frontlist, changeloglist
from urllib.parse import ParseResult, urlunparse, urlparse, quote, unquote
from os import path
import requests
from shutil import copyfile
from sys import stdout


snappyquotes = [f':#{x}:' for x in marseys_const2]

if path.exists(f'snappy_{SITE_ID}.txt'):
	with open(f'snappy_{SITE_ID}.txt', "r", encoding="utf-8") as f:
		snappyquotes += f.read().split("\n{[para]}\n")

discounts = {
	69: 0.02,
	70: 0.04,
	71: 0.06,
	72: 0.08,
	73: 0.10,
}

titleheaders = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.72 Safari/537.36"}

MAX_TITLE_LENGTH = 500
MAX_URL_LENGTH = 2048
MAX_BODY_LENGTH = 20000

# Get request value `val` and ensure it is within length constraints
# : Returns an either tuple (good_value, error)
# : TODO it may make sense to do more sanitisation here
def guarded_value(val, min_len, max_len):
	raw = request.values.get(val, '').strip()
	raw = raw.replace('\u200e', '')

	if len(raw) < min_len:
		return (None, ({"error": f"Minimum length for {val} is {min_len}"}, 403))

	if len(raw) > max_len:
		return (None, ({"error": f"Maximum length for {val} is {max_len}"}, 403))

	return (raw, None)

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
	
	if not post.ghost:
		notify_users = NOTIFY_USERS(f'{post.title} {post.body}', v)

		if notify_users:
			cid = notif_comment2(post)
			for x in notify_users:
				add_notif(cid, x)

		if v.followers:
			text = f"@{v.username} has made a new post: [{post.title}]({post.shortlink})"
			if post.sub: text += f" in <a href='/h/{post.sub}'>/h/{post.sub}"

			cid = notif_comment(text, autojanny=True)
			for follow in v.followers:
				user = get_account(follow.user_id)
				if post.club and not user.paid_dues: continue
				add_notif(cid, user.id)

	g.db.commit()

	cache.delete_memoized(frontlist)
	cache.delete_memoized(User.userpagelisting)

	if v.admin_level > 0 and ("[changelog]" in post.title.lower() or "(changelog)" in post.title.lower()):
		cache.delete_memoized(changeloglist)

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
		if request.headers.get("Authorization") or request.headers.get("xhr"): return {"error":"Must be 18+ to view"}, 451
		return render_template("errors/nsfw.html", v=v)

	if v: defaultsortingcomments = v.defaultsortingcomments
	else: defaultsortingcomments = "new"
	sort = request.values.get("sort", defaultsortingcomments)

	if post.club and not (v and (v.paid_dues or v.id == post.author_id)): abort(403)

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
		
		if not (v and v.shadowbanned) and not (v and v.admin_level > 2):
			comments = comments.join(User, User.id == Comment.author_id).filter(User.shadowbanned == None)

		if v.admin_level < 2:
			filter_clause = ((Comment.filter_state != 'filtered') & (Comment.filter_state != 'removed')) | (Comment.author_id == v.id)
			comments = comments.filter(filter_clause)

		comments=comments.filter(Comment.parent_submission == post.id).join(
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
		for c in comments.all():
			comment = c[0]
			comment.voted = c[1] or 0
			comment.is_blocking = c[2] or 0
			comment.is_blocked = c[3] or 0
			output.append(comment)
		
		pinned = [c[0] for c in comments.filter(Comment.is_pinned != None).all()]
		
		comments = comments.filter(Comment.level == 1, Comment.is_pinned == None)

		if sort == "new":
			comments = comments.order_by(Comment.created_utc.desc())
		elif sort == "old":
			comments = comments.order_by(Comment.created_utc)
		elif sort == "controversial":
			comments = comments.order_by((Comment.upvotes+1)/(Comment.downvotes+1) + (Comment.downvotes+1)/(Comment.upvotes+1), Comment.downvotes.desc())
		elif sort == "top":
			comments = comments.order_by(Comment.realupvotes.desc())
		elif sort == "bottom":
			comments = comments.order_by(Comment.upvotes - Comment.downvotes)

		comments = [c[0] for c in comments.all()]
	else:
		pinned = g.db.query(Comment).filter(Comment.parent_submission == post.id, Comment.is_pinned != None).all()

		comments = g.db.query(Comment).join(User, User.id == Comment.author_id).filter(User.shadowbanned == None, Comment.parent_submission == post.id, Comment.level == 1, Comment.is_pinned == None)

		if sort == "new":
			comments = comments.order_by(Comment.created_utc.desc())
		elif sort == "old":
			comments = comments.order_by(Comment.created_utc)
		elif sort == "controversial":
			comments = comments.order_by((Comment.upvotes+1)/(Comment.downvotes+1) + (Comment.downvotes+1)/(Comment.upvotes+1), Comment.downvotes.desc())
		elif sort == "top":
			comments = comments.order_by(Comment.realupvotes.desc())
		elif sort == "bottom":
			comments = comments.order_by(Comment.upvotes - Comment.downvotes)

		filter_clause = (Comment.filter_state != 'filtered') & (Comment.filter_state != 'removed')
		comments = comments.filter(filter_clause)

		comments = comments.all()

	offset = 0
	ids = set()

	limit = app.config['RESULTS_PER_PAGE_COMMENTS']

	if post.comment_count > limit and not request.headers.get("Authorization") and not request.values.get("all"):
		comments2 = []
		count = 0
		if post.created_utc > 1638672040:
			for comment in comments:
				comments2.append(comment)
				ids.add(comment.id)
				count += g.db.query(Comment.id).filter_by(parent_submission=post.id, top_comment_id=comment.id).count() + 1
				if count > limit: break
		else:
			for comment in comments:
				comments2.append(comment)
				ids.add(comment.id)
				count += g.db.query(Comment.id).filter_by(parent_submission=post.id, parent_comment_id=comment.id).count() + 1
				if count > limit: break

		if len(comments) == len(comments2): offset = 0
		else: offset = 1
		comments = comments2

	for pin in pinned:
		if pin.is_pinned_utc and int(time.time()) > pin.is_pinned_utc:
			pin.is_pinned = None
			pin.is_pinned_utc = None
			g.db.add(pin)
			pinned.remove(pin)

	post.replies = pinned + comments

	post.views += 1
	g.db.add(post)
	g.db.commit()
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

	offset = int(offset)
	try: ids = set(int(x) for x in request.values.get("ids").split(','))
	except: abort(400)
	
	if sort == "new":
		newest = g.db.query(Comment).filter(Comment.id.in_(ids)).order_by(Comment.created_utc.desc()).first()

	if v:
		votes = g.db.query(CommentVote).filter_by(user_id=v.id).subquery()

		blocking = v.blocking.subquery()

		blocked = v.blocked.subquery()

		comments = g.db.query(
			Comment,
			votes.c.vote_type,
			blocking.c.target_id,
			blocked.c.target_id,
		).filter(Comment.parent_submission == pid, Comment.is_pinned == None, Comment.id.notin_(ids))

		if not (v and v.shadowbanned) and not (v and v.admin_level > 2):
			comments = comments.join(User, User.id == Comment.author_id).filter(User.shadowbanned == None)

		if not v or v.admin_level < 2:
			filter_clause = (Comment.filter_state != 'filtered') & (Comment.filter_state != 'removed')
			if v:
				filter_clause = filter_clause | (Comment.author_id == v.id)
			comments = comments.filter(filter_clause)

		comments=comments.join(
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
		for c in comments.all():
			comment = c[0]
			comment.voted = c[1] or 0
			comment.is_blocking = c[2] or 0
			comment.is_blocked = c[3] or 0
			output.append(comment)
		
		comments = comments.filter(Comment.level == 1)

		if sort == "new":
			comments = comments.filter(Comment.created_utc < newest.created_utc)
			comments = comments.order_by(Comment.created_utc.desc())
		elif sort == "old":
			comments = comments.order_by(Comment.created_utc)
		elif sort == "controversial":
			comments = comments.order_by((Comment.upvotes+1)/(Comment.downvotes+1) + (Comment.downvotes+1)/(Comment.upvotes+1), Comment.downvotes.desc())
		elif sort == "top":
			comments = comments.order_by(Comment.realupvotes.desc())
		elif sort == "bottom":
			comments = comments.order_by(Comment.upvotes - Comment.downvotes)

		comments = [c[0] for c in comments.all()]
	else:
		comments = g.db.query(Comment).join(User, User.id == Comment.author_id).filter(User.shadowbanned == None, Comment.parent_submission == pid, Comment.level == 1, Comment.is_pinned == None, Comment.id.notin_(ids))

		if sort == "new":
			comments = comments.filter(Comment.created_utc < newest.created_utc)
			comments = comments.order_by(Comment.created_utc.desc())
		elif sort == "old":
			comments = comments.order_by(Comment.created_utc)
		elif sort == "controversial":
			comments = comments.order_by((Comment.upvotes+1)/(Comment.downvotes+1) + (Comment.downvotes+1)/(Comment.upvotes+1), Comment.downvotes.desc())
		elif sort == "top":
			comments = comments.order_by(Comment.realupvotes.desc())
		elif sort == "bottom":
			comments = comments.order_by(Comment.upvotes - Comment.downvotes)

		comments = comments.all()
		comments = comments[offset:]

	limit = app.config['RESULTS_PER_PAGE_COMMENTS']
	comments2 = []
	count = 0

	if post.created_utc > 1638672040:
		for comment in comments:
			comments2.append(comment)
			ids.add(comment.id)
			count += g.db.query(Comment.id).filter_by(parent_submission=post.id, top_comment_id=comment.id).count() + 1
			if count > limit: break
	else:
		for comment in comments:
			comments2.append(comment)
			ids.add(comment.id)
			count += g.db.query(Comment.id).filter_by(parent_submission=post.id, parent_comment_id=comment.id).count() + 1
			if count > limit: break
	
	if len(comments) == len(comments2): offset = 0
	else: offset += 1
	comments = comments2

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
		).filter(Comment.top_comment_id == tcid, Comment.level > 9).join(
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


@app.post("/edit_post/<pid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def edit_post(pid, v):
	p = get_post(pid)

	if p.author_id != v.id and not (v.admin_level > 1 and v.admin_level > 2): abort(403)

	title, err = guarded_value("title", 1, MAX_TITLE_LENGTH)
	if err: return err

	body, err = guarded_value("body", 0, MAX_BODY_LENGTH)
	if err: return err

	if title != p.title:
		p.title = title
		title_html = filter_emojis_only(title, edit=True)
		p.title_html = title_html

	if request.files.get("file") and request.headers.get("cf-ipcountry") != "T1":
		files = request.files.getlist('file')[:4]
		for file in files:
			if file.content_type.startswith('image/'):
				name = f'/images/{time.time()}'.replace('.','') + '.webp'
				file.save(name)
				url = process_image(name)
				if app.config['MULTIMEDIA_EMBEDDING_ENABLED']:
					body += f"\n\n![]({url})"
				else:
					body += f'\n\n<a href="{url}">{url}</a>'
			elif file.content_type.startswith('video/'):
				file.save("video.mp4")
				with open("video.mp4", 'rb') as f:
					try: req = requests.request("POST", "https://api.imgur.com/3/upload", headers={'Authorization': f'Client-ID {IMGUR_KEY}'}, files=[('video', f)], timeout=5).json()['data']
					except requests.Timeout: return {"error": "Video upload timed out, please try again!"}
					try: url = req['link']
					except:
						error = req['error']
						if error == 'File exceeds max duration': error += ' (60 seconds)'
						return {"error": error}, 400
				if url.endswith('.'): url += 'mp4'
				if app.config['MULTIMEDIA_EMBEDDING_ENABLED']:
					body += f"\n\n![]({url})"
				else:
					body += f'\n\n<a href="{url}">{url}</a>'
			else: return {"error": "Image/Video files only"}, 400

	body_html = sanitize(body, edit=True)

	p.body = body

	if len(body_html) > 40000: return {"error":"Submission body_html too long! (max 40k characters)"}, 400

	p.body_html = body_html

	if not p.private and not p.ghost:
		notify_users = NOTIFY_USERS(f'{p.title} {p.body}', v)
		if notify_users:
			cid = notif_comment2(p)
			for x in notify_users:
				add_notif(cid, x)

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
			"drama:thumbnail",
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

	for rd in ("://reddit.com", "://new.reddit.com", "://www.reddit.com", "://redd.it", "://libredd.it", "://teddit.net"):
		url = url.replace(rd, "://old.reddit.com")

	url = url.replace("nitter.net", "twitter.com").replace("old.reddit.com/gallery", "reddit.com/gallery").replace("https://youtu.be/", "https://youtube.com/watch?v=").replace("https://music.youtube.com/watch?v=", "https://youtube.com/watch?v=").replace("https://streamable.com/", "https://streamable.com/e/").replace("https://youtube.com/shorts/", "https://youtube.com/watch?v=").replace("https://mobile.twitter", "https://twitter").replace("https://m.facebook", "https://facebook").replace("m.wikipedia.org", "wikipedia.org").replace("https://m.youtube", "https://youtube").replace("https://www.youtube", "https://youtube").replace("https://www.twitter", "https://twitter").replace("https://www.instagram", "https://instagram").replace("https://www.tiktok", "https://tiktok")

	if "/i.imgur.com/" in url: url = url.replace(".png", ".webp").replace(".jpg", ".webp").replace(".jpeg", ".webp")
	elif "/media.giphy.com/" in url or "/c.tenor.com/" in url: url = url.replace(".gif", ".webp")
	elif "/i.ibb.com/" in url: url = url.replace(".png", ".webp").replace(".jpg", ".webp").replace(".jpeg", ".webp").replace(".gif", ".webp")

	if url.startswith("https://streamable.com/") and not url.startswith("https://streamable.com/e/"): url = url.replace("https://streamable.com/", "https://streamable.com/e/")

	parsed_url = urlparse(url)

	domain = parsed_url.netloc
	if domain in ('old.reddit.com','twitter.com','instagram.com','tiktok.com'):
		new_url = ParseResult(scheme="https",
				netloc=parsed_url.netloc,
				path=parsed_url.path,
				params=parsed_url.params,
				query=None,
				fragment=parsed_url.fragment)
	else:
		qd = parse_qs(parsed_url.query)
		filtered = {k: val for k, val in qd.items() if not k.startswith('utm_') and not k.startswith('ref_')}

		new_url = ParseResult(scheme="https",
							netloc=parsed_url.netloc,
							path=parsed_url.path,
							params=parsed_url.params,
							query=urlencode(filtered, doseq=True),
							fragment=parsed_url.fragment)
	
	url = urlunparse(new_url)

	if url.endswith('/'): url = url[:-1]

	search_url = url.replace('%', '').replace(r'\\', '').replace('_', r'\_').strip()
	repost = g.db.query(Submission).filter(
		Submission.url.ilike(search_url),
		Submission.deleted_utc == 0,
		Submission.is_banned == False
	).first()
	if repost: return {'permalink': repost.permalink}
	else: return {'permalink': ''}

@app.post("/submit")
# @app.post("/h/<sub>/submit")
@limiter.limit("1/second;2/minute;10/hour;50/day")
@auth_required
def submit_post(v, sub=None):

	def error(error):
		if request.headers.get("Authorization") or request.headers.get("xhr"): return {"error": error}, 403
	
		SUBS = [x[0] for x in g.db.query(Sub.name).order_by(Sub.name).all()]
		return render_template("submit.html", SUBS=SUBS, v=v, error=error, title=title, url=url, body=body), 400

	title, err = guarded_value("title", 1, MAX_TITLE_LENGTH)
	if err: return error(err[0]["error"])

	url, err = guarded_value("url", 0, MAX_URL_LENGTH)
	if err: return error(err[0]["error"])

	body, err = guarded_value("body", 0, MAX_BODY_LENGTH)
	if err: return error(err[0]["error"])

	sub = request.values.get("sub")
	if sub: sub = sub.replace('/h/','').replace('s/','')

	if sub and sub != 'none':
		sname = sub.strip().lower()
		sub = g.db.query(Sub.name).filter_by(name=sname).one_or_none()
		if not sub: return error(f"/h/{sname} not found!")
		sub = sub[0]
		if v.exiled_from(sub): return error(f"You're exiled from /h/{sub}")
	else: sub = None

	if v.is_suspended: return error("You can't perform this action while banned.")
	
	title_html = filter_emojis_only(title, graceful=True)

	if len(title_html) > 1500: return error("Rendered title is too big!")

	embed = None

	if url:
		for rd in ("://reddit.com", "://new.reddit.com", "://www.reddit.com", "://redd.it", "://libredd.it", "://teddit.net"):
			url = url.replace(rd, "://old.reddit.com")

		url = url.replace("nitter.net", "twitter.com").replace("old.reddit.com/gallery", "reddit.com/gallery").replace("https://youtu.be/", "https://youtube.com/watch?v=").replace("https://music.youtube.com/watch?v=", "https://youtube.com/watch?v=").replace("https://streamable.com/", "https://streamable.com/e/").replace("https://youtube.com/shorts/", "https://youtube.com/watch?v=").replace("https://mobile.twitter", "https://twitter").replace("https://m.facebook", "https://facebook").replace("m.wikipedia.org", "wikipedia.org").replace("https://m.youtube", "https://youtube").replace("https://www.youtube", "https://youtube").replace("https://www.twitter", "https://twitter").replace("https://www.instagram", "https://instagram").replace("https://www.tiktok", "https://tiktok")

		if "/i.imgur.com/" in url: url = url.replace(".png", ".webp").replace(".jpg", ".webp").replace(".jpeg", ".webp")
		elif "/media.giphy.com/" in url or "/c.tenor.com/" in url: url = url.replace(".gif", ".webp")
		elif "/i.ibb.com/" in url: url = url.replace(".png", ".webp").replace(".jpg", ".webp").replace(".jpeg", ".webp").replace(".gif", ".webp")

		if url.startswith("https://streamable.com/") and not url.startswith("https://streamable.com/e/"): url = url.replace("https://streamable.com/", "https://streamable.com/e/")

		parsed_url = urlparse(url)

		domain = parsed_url.netloc
		if domain in ('old.reddit.com','twitter.com','instagram.com','tiktok.com'):
			new_url = ParseResult(scheme="https",
					netloc=parsed_url.netloc,
					path=parsed_url.path,
					params=parsed_url.params,
					query=None,
					fragment=parsed_url.fragment)
		else:
			qd = parse_qs(parsed_url.query)
			filtered = {k: val for k, val in qd.items() if not k.startswith('utm_') and not k.startswith('ref_')}

			new_url = ParseResult(scheme="https",
								netloc=parsed_url.netloc,
								path=parsed_url.path,
								params=parsed_url.params,
								query=urlencode(filtered, doseq=True),
								fragment=parsed_url.fragment)
		
		url = urlunparse(new_url)

		if url.endswith('/'): url = url[:-1]

		search_url = sql_ilike_clean(url)
		repost = g.db.query(Submission).filter(
			Submission.url.ilike(search_url),
			Submission.deleted_utc == 0,
			Submission.is_banned == False
		).first()
		if repost and SITE != 'localhost': return redirect(repost.permalink)

		domain_obj = get_domain(domain)
		if not domain_obj: domain_obj = get_domain(domain+parsed_url.path)

		if domain_obj:
			reason = f"Remove the {domain_obj.domain} link from your post and try again. {domain_obj.reason}"
			return error(reason)
		elif "twitter.com" == domain:
			try: embed = requests.get("https://publish.twitter.com/oembed", params={"url":url, "omit_script":"t"}, timeout=5).json()["html"]
			except: pass
		elif url.startswith('https://youtube.com/watch?v='):
			url = unquote(url).replace('?t', '&t')
			yt_id = url.split('https://youtube.com/watch?v=')[1].split('&')[0].split('%')[0]

			if yt_id_regex.fullmatch(yt_id):
				req = requests.get(f"https://www.googleapis.com/youtube/v3/videos?id={yt_id}&key={YOUTUBE_KEY}&part=contentDetails", timeout=5).json()
				if req.get('items'):
					params = parse_qs(urlparse(url).query)
					t = params.get('t', params.get('start', [0]))[0]
					if isinstance(t, str): t = t.replace('s','')

					embed = f'<lite-youtube videoid="{yt_id}" params="autoplay=1&modestbranding=1'
					if t:
						try: embed += f'&start={int(t)}'
						except: pass
					embed += '"></lite-youtube>'
			
		elif app.config['SERVER_NAME'] in domain and "/post/" in url and "context" not in url:
			id = url.split("/post/")[1]
			if "/" in id: id = id.split("/")[0]
			embed = str(int(id))


	if not url and not body and not request.files.get("file") and not request.files.get("file2"):
		return error("Please enter a url or some text.")

	dup = g.db.query(Submission).filter(
		Submission.author_id == v.id,
		Submission.deleted_utc == 0,
		Submission.title == title,
		Submission.url == url,
		Submission.body == body
	).one_or_none()

	if dup and SITE != 'localhost': return redirect(dup.permalink)

	now = int(time.time())
	cutoff = now - 60 * 60 * 24


	similar_posts = g.db.query(Submission).filter(
					Submission.author_id == v.id,
					Submission.title.op('<->')(title) < app.config["SPAM_SIMILARITY_THRESHOLD"],
					Submission.created_utc > cutoff
	).all()

	if url:
		similar_urls = g.db.query(Submission).filter(
					Submission.author_id == v.id,
					Submission.url.op('<->')(url) < app.config["SPAM_URL_SIMILARITY_THRESHOLD"],
					Submission.created_utc > cutoff
		).all()
	else: similar_urls = []

	threshold = app.config["SPAM_SIMILAR_COUNT_THRESHOLD"]
	if v.age >= (60 * 60 * 24 * 7): threshold *= 3
	elif v.age >= (60 * 60 * 24): threshold *= 2

	if max(len(similar_urls), len(similar_posts)) >= threshold:

		text = "Your account has been banned for **1 day** for the following reason:\n\n> Too much spam!"
		send_repeatable_notification(v.id, text)

		v.ban(reason="Spamming.",
			  days=1)

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
		return redirect("/notifications")

	if request.files.get("file2") and request.headers.get("cf-ipcountry") != "T1":
		files = request.files.getlist('file2')[:4]
		for file in files:
			if file.content_type.startswith('image/'):
				name = f'/images/{time.time()}'.replace('.','') + '.webp'
				file.save(name)
				image = process_image(name)
				if app.config['MULTIMEDIA_EMBEDDING_ENABLED']:
					body += f"\n\n![]({image})"
				else:
					body += f'\n\n<a href="{image}">{image}</a>'
			elif file.content_type.startswith('video/'):
				file.save("video.mp4")
				with open("video.mp4", 'rb') as f:
					try: req = requests.request("POST", "https://api.imgur.com/3/upload", headers={'Authorization': f'Client-ID {IMGUR_KEY}'}, files=[('video', f)], timeout=5).json()['data']
					except requests.Timeout: return error("Video upload timed out, please try again!")
					try: url = req['link']
					except:
						err = req['error']
						if err == 'File exceeds max duration': err += ' (60 seconds)'
						return error(err)
				if url.endswith('.'): url += 'mp4'
				if app.config['MULTIMEDIA_EMBEDDING_ENABLED']:
					body += f"\n\n![]({url})"
				else:
					body += f'\n\n<a href="{url}">{url}</a>'
			else:
				return error("Image/Video files only.")

	body_html = sanitize(body)

	if len(body_html) > 40000: return error("Submission body_html too long! (max 40k characters)")

	club = bool(request.values.get("club",""))
	
	if embed and len(embed) > 1500: embed = None

	is_bot = bool(request.headers.get("Authorization"))

	# Invariant: these values are guarded and obey the length bound
	assert len(title) <= MAX_TITLE_LENGTH
	assert len(body) <= MAX_BODY_LENGTH

	post = Submission(
		private=bool(request.values.get("private","")),
		club=club,
		author_id=v.id,
		over_18=bool(request.values.get("over_18","")),
		app_id=v.client.application.id if v.client else None,
		is_bot = is_bot,
		url=url,
		body=body,
		body_html=body_html,
		embed_url=embed,
		title=title,
		title_html=title_html,
		sub=sub,
		ghost=False,
		filter_state='filtered' if v.admin_level == 0 and app.config['SETTINGS']['FilterNewPosts'] else 'normal'
	)

	g.db.add(post)
	g.db.flush()

	vote = Vote(user_id=v.id,
				vote_type=1,
				submission_id=post.id
				)
	g.db.add(vote)
	
	if request.files.get('file') and request.headers.get("cf-ipcountry") != "T1":

		file = request.files['file']

		if file.content_type.startswith('image/'):
			name = f'/images/{time.time()}'.replace('.','') + '.webp'
			file.save(name)
			post.url = process_image(name)

			name2 = name.replace('.webp', 'r.webp')
			copyfile(name, name2)
			post.thumburl = process_image(name2, resize=100)	
		elif file.content_type.startswith('video/'):
			file.save("video.mp4")
			with open("video.mp4", 'rb') as f:
				try: req = requests.request("POST", "https://api.imgur.com/3/upload", headers={'Authorization': f'Client-ID {IMGUR_KEY}'}, files=[('video', f)], timeout=5).json()['data']
				except requests.Timeout: return error("Video upload timed out, please try again!")
				try: url = req['link']
				except:
					err = req['error']
					if err == 'File exceeds max duration': err += ' (60 seconds)'
					return error(err)
			if url.endswith('.'): url += 'mp4'
			post.url = url
		else:
			return error("Image/Video files only.")
		
	if not post.thumburl and post.url:
		gevent.spawn(thumbnail_thread, post.id)

	if not post.private and not post.ghost:

		notify_users = NOTIFY_USERS(f'{title} {body}', v)

		if notify_users:
			cid = notif_comment2(post)
			for x in notify_users:
				add_notif(cid, x)

		if (request.values.get('followers') or is_bot) and v.followers:
			text = f"@{v.username} has made a new post: [{post.title}]({post.shortlink})"
			if post.sub: text += f" in <a href='/h/{post.sub}'>/h/{post.sub}"

			cid = notif_comment(text, autojanny=True)
			for follow in v.followers:
				user = get_account(follow.user_id)
				if post.club and not user.paid_dues: continue
				add_notif(cid, user.id)

	v.post_count = g.db.query(Submission.id).filter_by(author_id=v.id, is_banned=False, deleted_utc=0).count()
	g.db.add(v)
	g.db.commit()

	cache.delete_memoized(frontlist)
	cache.delete_memoized(User.userpagelisting)

	if v.admin_level > 0 and ("[changelog]" in post.title.lower() or "(changelog)" in post.title.lower()) and not post.private:
		cache.delete_memoized(changeloglist)

	if request.headers.get("Authorization"): return post.json
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

	cache.delete_memoized(frontlist)

	g.db.commit()

	return {"message": "Post deleted!"}

@app.post("/undelete_post/<pid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def undelete_post_pid(pid, v):
	post = get_post(pid)
	if post.author_id != v.id: abort(403)
	post.deleted_utc =0
	g.db.add(post)

	cache.delete_memoized(frontlist)

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

	post = g.db.query(Submission).filter_by(id=post_id).one_or_none()
	if post:
		if v.id != post.author_id: return {"error": "Only the post author's can do that!"}
		post.is_pinned = not post.is_pinned
		g.db.add(post)

		cache.delete_memoized(User.userpagelisting)

		g.db.commit()
		if post.is_pinned: return {"message": "Post pinned!"}
		else: return {"message": "Post unpinned!"}
	return {"error": "Post not found!"}


@app.get("/submit/title")
@limiter.limit("6/minute")
@auth_required
def get_post_title(v):

	url = request.values.get("url")
	if not url: abort(400)

	try: x = requests.get(url, headers=titleheaders, timeout=5, proxies=proxies)
	except: abort(400)

	soup = BeautifulSoup(x.content, 'lxml')

	title = soup.find('title')
	if not title: abort(400)

	return {"url": url, "title": title.string}
