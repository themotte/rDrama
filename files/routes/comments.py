from files.helpers.wrappers import *
from files.helpers.alerts import *
from files.helpers.images import *
from files.helpers.const import *
from files.classes import *
from pusher_push_notifications import PushNotifications
from flask import *
from files.__main__ import app, limiter
from files.helpers.sanitize import filter_emojis_only
from files.helpers.assetcache import assetcache_path
import requests
from shutil import copyfile
from json import loads
from collections import Counter
import gevent
from sys import stdout

if PUSHER_ID != 'blahblahblah':
	beams_client = PushNotifications(instance_id=PUSHER_ID, secret_key=PUSHER_KEY)

def pusher_thread(interests, c, username):
	if len(c.body) > 500: notifbody = c.body[:500] + '...'
	else: notifbody = c.body

	beams_client.publish_to_interests(
		interests=[interests],
		publish_body={
			'web': {
				'notification': {
					'title': f'New reply by @{username}',
					'body': notifbody,
					'deep_link': f'{SITE_FULL}/comment/{c.id}?context=8&read=true#context',
					'icon': SITE_FULL + assetcache_path(f'images/{SITE_ID}/icon.webp'),
				}
			},
			'fcm': {
				'notification': {
					'title': f'New reply by @{username}',
					'body': notifbody,
				},
				'data': {
					'url': f'/comment/{c.id}?context=8&read=true#context',
				}
			}
		},
	)
	stdout.flush()

@app.get("/comment/<cid>")
@app.get("/post/<pid>/<anything>/<cid>")
# @app.get("/h/<sub>/comment/<cid>")
# @app.get("/h/<sub>/post/<pid>/<anything>/<cid>")
@auth_desired
def post_pid_comment_cid(cid, pid=None, anything=None, v=None, sub=None):

	try: cid = int(cid)
	except: abort(404)

	comment = get_comment(cid, v=v)
	
	if v and request.values.get("read"):
		notif = g.db.query(Notification).filter_by(comment_id=cid, user_id=v.id, read=False).one_or_none()
		if notif:
			notif.read = True
			g.db.add(notif)
			g.db.commit()

	if comment.post and comment.post.club and not (v and (v.paid_dues or v.id in [comment.author_id, comment.post.author_id])): abort(403)

	if comment.post and comment.post.private and not (v and (v.admin_level > 1 or v.id == comment.post.author.id)): abort(403)

	if not comment.parent_submission and not (v and (comment.author.id == v.id or comment.sentto == v.id)) and not (v and v.admin_level > 1) : abort(403)
	
	if not pid:
		if comment.parent_submission: pid = comment.parent_submission
		else: pid = 1
	
	try: pid = int(pid)
	except: abort(404)
	
	post = get_post(pid, v=v)
	
	if post.over_18 and not (v and v.over_18) and not session.get('over_18', 0) >= int(time.time()):
		if request.headers.get("Authorization"): return {'error': 'This content is not suitable for some users and situations.'}
		else: return render_template("errors/nsfw.html", v=v)

	try: context = min(int(request.values.get("context", 0)), 8)
	except: context = 0
	comment_info = comment
	c = comment
	while context and c.level > 1:
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

		if not (v and v.shadowbanned) and not (v and v.admin_level > 2):
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
		if post.is_banned and not (v and (v.admin_level > 1 or post.author_id == v.id)): template = "submission_banned.html"
		else: template = "submission.html"
		return render_template(template, v=v, p=post, sort=sort, comment_info=comment_info, render_replies=True, sub=post.subr)

@app.post("/comment")
@limiter.limit("1/second;20/minute;200/hour;1000/day")
@auth_required
def api_comment(v):
	if v.is_suspended: return {"error": "You can't perform this action while banned."}, 403

	parent_fullname = request.values.get("parent_fullname").strip()

	if len(parent_fullname) < 3: abort(400)
	id = parent_fullname[2:]
	parent = None
	parent_post = None
	parent_comment_id = None

	if parent_fullname.startswith("p_"):
		parent = get_post(id, v=v)
		parent_post = parent
	elif parent_fullname.startswith("c_"):
		parent = get_comment(id, v=v)
		parent_post = get_post(parent.parent_submission, v=v) if parent.parent_submission else None
		parent_comment_id = parent.id
	else: abort(400)
	if not parent_post: abort(404) # don't allow sending comments to the ether
	level = 1 if isinstance(parent, Submission) else parent.level + 1

	body = request.values.get("body", "").strip()[:10000]

	if parent_post.id not in ADMINISTRATORS:
		if v.longpost and (len(body) < 280 or ' [](' in body or body.startswith('[](')):
			return {"error":"You have to type more than 280 characters!"}, 403
		elif v.bird and len(body) > 140:
			return {"error":"You have to type less than 140 characters!"}, 403

	if not body and not request.files.get('file'): return {"error":"You need to actually write something!"}, 400

	if request.files.get("file") and request.headers.get("cf-ipcountry") != "T1":
		files = request.files.getlist('file')[:4]
		for file in files:
			if file.content_type.startswith('image/'):
				oldname = f'/images/{time.time()}'.replace('.','') + '.webp'
				file.save(oldname)
				image = process_image(oldname)
				if image == "": return {"error":"Image upload failed"}
				if v.admin_level > 2 and level == 1:
					if parent_post.id == 37696:
						pass
						# filename = 'files/assets/images/rDrama/sidebar/' + str(len(listdir('files/assets/images/rDrama/sidebar'))+1) + '.webp'
						# copyfile(oldname, filename)
						# process_image(filename, 400)
					elif parent_post.id == 37697:
						pass
						# filename = 'files/assets/images/rDrama/banners/' + str(len(listdir('files/assets/images/rDrama/banners'))+1) + '.webp'
						# copyfile(oldname, filename)
						# process_image(filename)
					elif parent_post.id == 37833:
						try:
							badge_def = loads(body)
							name = badge_def["name"]

							existing = g.db.query(BadgeDef).filter_by(name=name).one_or_none()
							if existing: return {"error": "A badge with this name already exists!"}, 403

							badge = BadgeDef(name=name, description=badge_def["description"])
							g.db.add(badge)
							g.db.flush()
							filename = f'files/assets/images/badges/{badge.id}.webp'
							copyfile(oldname, filename)
							process_image(filename, 200)
							requests.post(f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE}/purge_cache', headers=CF_HEADERS, data={'files': [f"https://{request.host}/assets/images/badges/{badge.id}.webp"]}, timeout=5)
						except Exception as e:
							return {"error": str(e)}, 400
				if app.config['MULTIMEDIA_EMBEDDING_ENABLED']:
					body += f"\n\n![]({image})"
				else:
					body += f'\n\n<a href="{image}">{image}</a>'
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
					body += f"\n\n{url}"
				else:
					body += f'\n\n<a href="{url}">{url}</a>'
			else: return {"error": "Image/Video files only"}, 400

	body_html = sanitize(body, comment=True)

	if parent_post.id not in ADMINISTRATORS:
		existing = g.db.query(Comment.id).filter(Comment.author_id == v.id,
																	Comment.deleted_utc == 0,
																	Comment.parent_comment_id == parent_comment_id,
																	Comment.parent_submission == parent_post.id,
																	Comment.body_html == body_html
																	).one_or_none()
		if existing: return {"error": f"You already made that comment: /comment/{existing.id}"}, 409

	if parent.author.any_block_exists(v) and v.admin_level < 2:
		return {"error": "You can't reply to users who have blocked you, or users you have blocked."}, 403

	is_bot = bool(request.headers.get("Authorization"))

	if parent_post.id not in ADMINISTRATORS and not is_bot and not v.marseyawarded and len(body) > 10:
		now = int(time.time())
		cutoff = now - 60 * 60 * 24

		similar_comments = g.db.query(Comment).filter(
			Comment.author_id == v.id,
			Comment.body.op(
				'<->')(body) < app.config["COMMENT_SPAM_SIMILAR_THRESHOLD"],
			Comment.created_utc > cutoff
		).all()

		threshold = app.config["COMMENT_SPAM_COUNT_THRESHOLD"]
		if v.age >= (60 * 60 * 24 * 7):
			threshold *= 3
		elif v.age >= (60 * 60 * 24):
			threshold *= 2

		if len(similar_comments) > threshold:
			text = "Your account has been banned for **1 day** for the following reason:\n\n> Too much spam!"
			send_repeatable_notification(v.id, text)

			v.ban(reason="Spamming.",
					days=1)

			for comment in similar_comments:
				comment.is_banned = True
				comment.ban_reason = "AutoJanny"
				g.db.add(comment)
				ma=ModAction(
					user_id=AUTOJANNY_ID,
					target_comment_id=comment.id,
					kind="ban_comment",
					_note="spam"
					)
				g.db.add(ma)

			return {"error": "Too much spam!"}, 403

	if len(body_html) > 20000: abort(400)

	is_filtered = v.should_comments_be_filtered()

	c = Comment(author_id=v.id,
				parent_submission=parent_post.id,
				parent_comment_id=parent_comment_id,
				level=level,
				over_18=parent_post.over_18 or request.values.get("over_18")=="true",
				is_bot=is_bot,
				app_id=v.client.application.id if v.client else None,
				body_html=body_html,
				body=body[:10000],
				ghost=parent_post.ghost,
				filter_state='filtered' if is_filtered else 'normal'
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
	
	if v.id == PIZZASHILL_ID:
		for uid in PIZZA_VOTERS:
			autovote = CommentVote(user_id=uid, comment_id=c.id, vote_type=1)
			g.db.add(autovote)
		v.coins += 3
		v.truecoins += 3
		g.db.add(v)
		c.upvotes += 3
		g.db.add(c)

	if v.marseyawarded and parent_post.id not in ADMINISTRATORS and marseyaward_body_regex.search(body_html):
		return {"error":"You can only type marseys!"}, 403

	g.db.commit()

	if request.headers.get("Authorization"): return c.json
	return {"comment": render_template("comments.html", v=v, comments=[c], ajax=True, parent_level=level)}


def comment_on_publish(comment):
	"""
	Run when comment becomes visible: immediately for non-filtered comments,
	or on approval for previously filtered comments.
	Should be used to update stateful counters, notifications, etc. that
	reflect the comments users will actually see.
	"""
	# TODO: Get this out of the routes and into a model eventually...

	# Shadowbanned users are invisible. This may lead to inconsistencies if
	# a user comments while shadowed and is later unshadowed. (TODO?)
	if comment.author.shadowbanned:
		return

	# Comment instances used for purposes other than actual comments (notifs,
	# DMs) shouldn't be considered published.
	if not comment.parent_submission:
		return

	# Generate notifs for: mentions, post subscribers, parent post/comment
	to_notify = NOTIFY_USERS(comment.body, comment.author)

	post_subscribers = g.db.query(Subscription.user_id).filter(
			Subscription.submission_id == comment.parent_submission,
			Subscription.user_id != comment.author_id,
		).all()
	to_notify.update([x[0] for x in post_subscribers])

	parent = comment.parent
	if parent and parent.author_id != comment.author_id:
		to_notify.add(parent.author_id)

	for uid in to_notify:
		notif = Notification(comment_id=comment.id, user_id=uid)
		g.db.add(notif)

	# Comment counter for parent submission
	comment.post.comment_count += 1
	g.db.add(comment.post)

	# Comment counter for author's profile
	comment.author.comment_count = g.db.query(Comment).filter(
			Comment.author_id == comment.author_id,
			Comment.parent_submission != None,
			Comment.is_banned == False,
			Comment.deleted_utc == 0,
		).count()
	g.db.add(comment.author)

	# Generate push notifications if enabled.
	if PUSHER_ID != 'blahblahblah' and comment.author_id != parent.author_id:
		try:
			gevent.spawn(pusher_thread, f'{request.host}{parent.author.id}',
				comment, comment.author_name)
		except: pass


@app.post("/edit_comment/<cid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def edit_comment(cid, v):

	c = get_comment(cid, v=v)

	if c.author_id != v.id: abort(403)

	body = request.values.get("body", "").strip()[:10000]

	if len(body) < 1 and not (request.files.get("file") and request.headers.get("cf-ipcountry") != "T1"):
		return {"error":"You have to actually type something!"}, 400

	if body != c.body or request.files.get("file") and request.headers.get("cf-ipcountry") != "T1":
		if v.longpost and (len(body) < 280 or ' [](' in body or body.startswith('[](')):
			return {"error":"You have to type more than 280 characters!"}, 403
		elif v.bird and len(body) > 140:
			return {"error":"You have to type less than 140 characters!"}, 403

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
		if v.age >= (60 * 60 * 24 * 30):
			threshold *= 4
		elif v.age >= (60 * 60 * 24 * 7):
			threshold *= 3
		elif v.age >= (60 * 60 * 24):
			threshold *= 2

		if len(similar_comments) > threshold:
			text = "Your account has been banned for **1 day** for the following reason:\n\n> Too much spam!"
			send_repeatable_notification(v.id, text)

			v.ban(reason="Spamming.",
					days=1)

			for comment in similar_comments:
				comment.is_banned = True
				comment.ban_reason = "AutoJanny"
				g.db.add(comment)

			return {"error": "Too much spam!"}, 403
		# End Spam Checking

		if request.files.get("file") and request.headers.get("cf-ipcountry") != "T1":
			files = request.files.getlist('file')[:4]
			for file in files:
				if file.content_type.startswith('image/'):
					name = f'/images/{time.time()}'.replace('.','') + '.webp'
					file.save(name)
					url = process_image(name)
					body += f"\n\n![]({url})"
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
					body += f"\n\n{url}"
				else: return {"error": "Image/Video files only"}, 400

			body_html = sanitize(body, edit=True)

		if len(body_html) > 20000: abort(400)

		if v.marseyawarded and marseyaward_body_regex.search(body_html):
			return {"error":"You can only type marseys!"}, 403

		c.body = body[:10000]
		c.body_html = body_html

		if int(time.time()) - c.created_utc > 60 * 3: c.edited_utc = int(time.time())

		g.db.add(c)
		
		if c.filter_state != 'filtered':
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

	if not c.deleted_utc:

		if c.author_id != v.id: abort(403)

		c.deleted_utc = int(time.time())

		g.db.add(c)
		g.db.commit()

	return {"message": "Comment deleted!"}

@app.post("/undelete/comment/<cid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def undelete_comment(cid, v):

	c = get_comment(cid, v=v)

	if c.deleted_utc:
		if c.author_id != v.id: abort(403)

		c.deleted_utc = 0

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
			return {"error": "You can only unpin comments you have pinned!"}

		comment.is_pinned = None
		g.db.add(comment)

		if v.id != comment.author_id:
			message = f"@{v.username} (OP) has unpinned your [comment]({comment.shortlink})!"
			send_repeatable_notification(comment.author_id, message)
		g.db.commit()
	return {"message": "Comment unpinned!"}


@app.post("/mod_pin/<cid>")
@auth_required
def mod_pin(cid, v):
	
	comment = get_comment(cid, v=v)
	
	if not comment.is_pinned:
		if not (comment.post.sub and v.mods(comment.post.sub)): abort(403)
		
		comment.is_pinned = v.username + " (Mod)"

		g.db.add(comment)

		if v.id != comment.author_id:
			message = f"@{v.username} (Mod) has pinned your [comment]({comment.shortlink})!"
			send_repeatable_notification(comment.author_id, message)

		g.db.commit()
	return {"message": "Comment pinned!"}
	

@app.post("/unmod_pin/<cid>")
@auth_required
def mod_unpin(cid, v):
	
	comment = get_comment(cid, v=v)
	
	if comment.is_pinned:
		if not (comment.post.sub and v.mods(comment.post.sub)): abort(403)

		comment.is_pinned = None
		g.db.add(comment)

		if v.id != comment.author_id:
			message = f"@{v.username} (Mod) has unpinned your [comment]({comment.shortlink})!"
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
