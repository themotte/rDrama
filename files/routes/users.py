import qrcode
import io
import time
import math

from files.classes.leaderboard import SimpleLeaderboard, BadgeMarseyLeaderboard, UserBlockLeaderboard, LeaderboardMeta
from files.classes.views import ViewerRelationship
from files.helpers.alerts import *
from files.helpers.sanitize import *
from files.helpers.strings import sql_ilike_clean
from files.helpers.const import *
from files.helpers.assetcache import assetcache_path
from files.helpers.contentsorting import apply_time_filter, sort_objects
from files.mail import *
from flask import *
from files.__main__ import app, limiter
from collections import Counter
import gevent

# warning: do not move currently. these have import-time side effects but 
# until this is refactored to be not completely awful, there's not really
# a better option.
from files.helpers.services import * 

@app.get("/@<username>/upvoters/<uid>/posts")
@admin_level_required(3)
def upvoters_posts(v, username, uid):
	u = get_user(username)
	if u.is_private and v.id != u.id: abort(403)
	id = u.id
	uid = int(uid)

	page = max(1, int(request.values.get("page", 1)))

	listing = g.db.query(Submission).join(Vote, Vote.submission_id==Submission.id).filter(Submission.ghost == False, Submission.is_banned == False, Submission.deleted_utc == 0, Vote.vote_type==1, Submission.author_id==id, Vote.user_id==uid).order_by(Submission.created_utc.desc()).offset(25 * (page - 1)).limit(26).all()

	listing = [p.id for p in listing]
	next_exists = len(listing) > 25
	listing = listing[:25]

	listing = get_posts(listing, v=v, eager=True)

	return render_template("voted_posts.html", next_exists=next_exists, listing=listing, page=page, v=v)


@app.get("/@<username>/upvoters/<uid>/comments")
@admin_level_required(3)
def upvoters_comments(v, username, uid):
	u = get_user(username)
	if u.is_private and v.id != u.id: abort(403)
	id = u.id
	uid = int(uid)

	page = max(1, int(request.values.get("page", 1)))

	listing = g.db.query(Comment).join(CommentVote, CommentVote.comment_id==Comment.id).filter(Comment.ghost == False, Comment.is_banned == False, Comment.deleted_utc == 0, CommentVote.vote_type==1, Comment.author_id==id, CommentVote.user_id==uid).order_by(Comment.created_utc.desc()).offset(25 * (page - 1)).limit(26).all()

	listing = [c.id for c in listing]
	next_exists = len(listing) > 25
	listing = listing[:25]

	listing = get_comments(listing, v=v)

	return render_template("voted_comments.html", next_exists=next_exists, listing=listing, page=page, v=v, standalone=True)


@app.get("/@<username>/downvoters/<uid>/posts")
@admin_level_required(3)
def downvoters_posts(v, username, uid):
	u = get_user(username)
	if u.is_private and v.id != u.id: abort(403)
	id = u.id
	uid = int(uid)

	page = max(1, int(request.values.get("page", 1)))

	listing = g.db.query(Submission).join(Vote, Vote.submission_id==Submission.id).filter(Submission.ghost == False, Submission.is_banned == False, Submission.deleted_utc == 0, Vote.vote_type==-1, Submission.author_id==id, Vote.user_id==uid).order_by(Submission.created_utc.desc()).offset(25 * (page - 1)).limit(26).all()

	listing = [p.id for p in listing]
	next_exists = len(listing) > 25
	listing = listing[:25]

	listing = get_posts(listing, v=v, eager=True)

	return render_template("voted_posts.html", next_exists=next_exists, listing=listing, page=page, v=v)


@app.get("/@<username>/downvoters/<uid>/comments")
@admin_level_required(3)
def downvoters_comments(v, username, uid):
	u = get_user(username)
	if u.is_private and v.id != u.id: abort(403)
	id = u.id
	uid = int(uid)

	page = max(1, int(request.values.get("page", 1)))

	listing = g.db.query(Comment).join(CommentVote, CommentVote.comment_id==Comment.id).filter(Comment.ghost == False, Comment.is_banned == False, Comment.deleted_utc == 0, CommentVote.vote_type==-1, Comment.author_id==id, CommentVote.user_id==uid).order_by(Comment.created_utc.desc()).offset(25 * (page - 1)).limit(26).all()

	listing = [c.id for c in listing]
	next_exists = len(listing) > 25
	listing = listing[:25]

	listing = get_comments(listing, v=v)

	return render_template("voted_comments.html", next_exists=next_exists, listing=listing, page=page, v=v, standalone=True)

@app.get("/@<username>/upvoting/<uid>/posts")
@admin_level_required(3)
def upvoting_posts(v, username, uid):
	u = get_user(username)
	if u.is_private and v.id != u.id: abort(403)
	id = u.id
	uid = int(uid)

	page = max(1, int(request.values.get("page", 1)))

	listing = g.db.query(Submission).join(Vote, Vote.submission_id==Submission.id).filter(Submission.ghost == False, Submission.is_banned == False, Submission.deleted_utc == 0, Vote.vote_type==1, Vote.user_id==id, Submission.author_id==uid).order_by(Submission.created_utc.desc()).offset(25 * (page - 1)).limit(26).all()

	listing = [p.id for p in listing]
	next_exists = len(listing) > 25
	listing = listing[:25]

	listing = get_posts(listing, v=v, eager=True)

	return render_template("voted_posts.html", next_exists=next_exists, listing=listing, page=page, v=v)


@app.get("/@<username>/upvoting/<uid>/comments")
@admin_level_required(3)
def upvoting_comments(v, username, uid):
	u = get_user(username)
	if u.is_private and v.id != u.id: abort(403)
	id = u.id
	uid = int(uid)

	page = max(1, int(request.values.get("page", 1)))

	listing = g.db.query(Comment).join(CommentVote, CommentVote.comment_id==Comment.id).filter(Comment.ghost == False, Comment.is_banned == False, Comment.deleted_utc == 0, CommentVote.vote_type==1, CommentVote.user_id==id, Comment.author_id==uid).order_by(Comment.created_utc.desc()).offset(25 * (page - 1)).limit(26).all()

	listing = [c.id for c in listing]
	next_exists = len(listing) > 25
	listing = listing[:25]

	listing = get_comments(listing, v=v)

	return render_template("voted_comments.html", next_exists=next_exists, listing=listing, page=page, v=v, standalone=True)


@app.get("/@<username>/downvoting/<uid>/posts")
@admin_level_required(3)
def downvoting_posts(v, username, uid):
	u = get_user(username)
	if u.is_private and v.id != u.id: abort(403)
	id = u.id
	uid = int(uid)

	page = max(1, int(request.values.get("page", 1)))

	listing = g.db.query(Submission).join(Vote, Vote.submission_id==Submission.id).filter(Submission.ghost == False, Submission.is_banned == False, Submission.deleted_utc == 0, Vote.vote_type==-1, Vote.user_id==id, Submission.author_id==uid).order_by(Submission.created_utc.desc()).offset(25 * (page - 1)).limit(26).all()

	listing = [p.id for p in listing]
	next_exists = len(listing) > 25
	listing = listing[:25]

	listing = get_posts(listing, v=v, eager=True)

	return render_template("voted_posts.html", next_exists=next_exists, listing=listing, page=page, v=v)


@app.get("/@<username>/downvoting/<uid>/comments")
@admin_level_required(3)
def downvoting_comments(v, username, uid):
	u = get_user(username)
	if u.is_private and v.id != u.id: abort(403)
	id = u.id
	uid = int(uid)

	page = max(1, int(request.values.get("page", 1)))

	listing = g.db.query(Comment).join(CommentVote, CommentVote.comment_id==Comment.id).filter(Comment.ghost == False, Comment.is_banned == False, Comment.deleted_utc == 0, CommentVote.vote_type==-1, CommentVote.user_id==id, Comment.author_id==uid).order_by(Comment.created_utc.desc()).offset(25 * (page - 1)).limit(26).all()

	listing = [c.id for c in listing]
	next_exists = len(listing) > 25
	listing = listing[:25]

	listing = get_comments(listing, v=v)

	return render_template("voted_comments.html", next_exists=next_exists, listing=listing, page=page, v=v, standalone=True)

@app.get("/@<username>/upvoters")
@admin_level_required(3)
def upvoters(v, username):
	id = get_user(username).id

	votes = g.db.query(Vote.user_id, func.count(Vote.user_id)).join(Submission, Vote.submission_id==Submission.id).filter(Submission.ghost == False, Submission.is_banned == False, Submission.deleted_utc == 0, Vote.vote_type==1, Submission.author_id==id).group_by(Vote.user_id).order_by(func.count(Vote.user_id).desc()).all()

	votes2 = g.db.query(CommentVote.user_id, func.count(CommentVote.user_id)).join(Comment, CommentVote.comment_id==Comment.id).filter(Comment.ghost == False, Comment.is_banned == False, Comment.deleted_utc == 0, CommentVote.vote_type==1, Comment.author_id==id).group_by(CommentVote.user_id).order_by(func.count(CommentVote.user_id).desc()).all()

	votes = Counter(dict(votes)) + Counter(dict(votes2))

	users = g.db.query(User).filter(User.id.in_(votes.keys())).all()
	users2 = []
	for user in users: users2.append((user, votes[user.id]))

	users = sorted(users2, key=lambda x: x[1], reverse=True)
	
	try:
		pos = [x[0].id for x in users].index(v.id)
		pos = (pos+1, users[pos][1])
	except: pos = (len(users)+1, 0)

	return render_template("voters.html", v=v, users=users[:25], pos=pos, name='Up', name2=f'Who upvotes @{username}')



@app.get("/@<username>/downvoters")
@admin_level_required(3)
def downvoters(v, username):
	id = get_user(username).id

	votes = g.db.query(Vote.user_id, func.count(Vote.user_id)).join(Submission, Vote.submission_id==Submission.id).filter(Submission.ghost == False, Submission.is_banned == False, Submission.deleted_utc == 0, Vote.vote_type==-1, Submission.author_id==id).group_by(Vote.user_id).order_by(func.count(Vote.user_id).desc()).all()

	votes2 = g.db.query(CommentVote.user_id, func.count(CommentVote.user_id)).join(Comment, CommentVote.comment_id==Comment.id).filter(Comment.ghost == False, Comment.is_banned == False, Comment.deleted_utc == 0, CommentVote.vote_type==-1, Comment.author_id==id).group_by(CommentVote.user_id).order_by(func.count(CommentVote.user_id).desc()).all()

	votes = Counter(dict(votes)) + Counter(dict(votes2))

	users = g.db.query(User).filter(User.id.in_(votes.keys())).all()
	users2 = []
	for user in users: users2.append((user, votes[user.id]))

	users = sorted(users2, key=lambda x: x[1], reverse=True)
	
	try:
		pos = [x[0].id for x in users].index(v.id)
		pos = (pos+1, users[pos][1])
	except: pos = (len(users)+1, 0)

	return render_template("voters.html", v=v, users=users[:25], pos=pos, name='Down', name2=f'Who downvotes @{username}')

@app.get("/@<username>/upvoting")
@admin_level_required(3)
def upvoting(v, username):
	id = get_user(username).id

	votes = g.db.query(Submission.author_id, func.count(Submission.author_id)).join(Vote, Vote.submission_id==Submission.id).filter(Submission.ghost == False, Submission.is_banned == False, Submission.deleted_utc == 0, Vote.vote_type==1, Vote.user_id==id).group_by(Submission.author_id).order_by(func.count(Submission.author_id).desc()).all()

	votes2 = g.db.query(Comment.author_id, func.count(Comment.author_id)).join(CommentVote, CommentVote.comment_id==Comment.id).filter(Comment.ghost == False, Comment.is_banned == False, Comment.deleted_utc == 0, CommentVote.vote_type==1, CommentVote.user_id==id).group_by(Comment.author_id).order_by(func.count(Comment.author_id).desc()).all()

	votes = Counter(dict(votes)) + Counter(dict(votes2))

	users = g.db.query(User).filter(User.id.in_(votes.keys())).all()
	users2 = []
	for user in users: users2.append((user, votes[user.id]))

	users = sorted(users2, key=lambda x: x[1], reverse=True)
	
	try:
		pos = [x[0].id for x in users].index(v.id)
		pos = (pos+1, users[pos][1])
	except: pos = (len(users)+1, 0)

	return render_template("voters.html", v=v, users=users[:25], pos=pos, name='Up', name2=f'Who @{username} upvotes')

@app.get("/@<username>/downvoting")
@admin_level_required(3)
def downvoting(v, username):
	id = get_user(username).id

	votes = g.db.query(Submission.author_id, func.count(Submission.author_id)).join(Vote, Vote.submission_id==Submission.id).filter(Submission.ghost == False, Submission.is_banned == False, Submission.deleted_utc == 0, Vote.vote_type==-1, Vote.user_id==id).group_by(Submission.author_id).order_by(func.count(Submission.author_id).desc()).all()

	votes2 = g.db.query(Comment.author_id, func.count(Comment.author_id)).join(CommentVote, CommentVote.comment_id==Comment.id).filter(Comment.ghost == False, Comment.is_banned == False, Comment.deleted_utc == 0, CommentVote.vote_type==-1, CommentVote.user_id==id).group_by(Comment.author_id).order_by(func.count(Comment.author_id).desc()).all()

	votes = Counter(dict(votes)) + Counter(dict(votes2))

	users = g.db.query(User).filter(User.id.in_(votes.keys())).all()
	users2 = []
	for user in users: users2.append((user, votes[user.id]))

	users = sorted(users2, key=lambda x: x[1], reverse=True)
	
	try:
		pos = [x[0].id for x in users].index(v.id)
		pos = (pos+1, users[pos][1])
	except: pos = (len(users)+1, 0)

	return render_template("voters.html", v=v, users=users[:25], pos=pos, name='Down', name2=f'Who @{username} downvotes')


@app.post("/@<username>/transfer_coins")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@is_not_permabanned
def transfer_coins(v, username):
	abort(404) # disable entirely pending possible future use of coins

	receiver = g.db.query(User).filter_by(username=username).one_or_none()

	if receiver is None: abort(404, "That user doesn't exist.")

	if receiver.id != v.id:
		amount = request.values.get("amount", "").strip()
		amount = int(amount) if amount.isdigit() else None

		if amount is None or amount <= 0: abort(400, "Invalid amount of coins.")
		if v.coins < amount: abort(400, "You don't have enough coins.")
		if amount < 100: abort(400, "You have to gift at least 100 coins.")

		if not v.patron and not receiver.patron and not v.alts_patron and not receiver.alts_patron: tax = math.ceil(amount*0.03)
		else: tax = 0

		log_message = f"@{v.username} has transferred {amount} coins to @{receiver.username}"
		send_repeatable_notification(GIFT_NOTIF_ID, log_message)

		receiver.coins += amount-tax
		v.coins -= amount
		send_repeatable_notification(receiver.id, f":marseycapitalistmanlet: @{v.username} has gifted you {amount-tax} coins!")
		g.db.add(receiver)
		g.db.add(v)

		g.db.commit()
		return {"message": f"{amount-tax} coins transferred!"}, 200

	return {"message": "You can't transfer coins to yourself!"}, 400


@app.post("/@<username>/transfer_bux")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@is_not_permabanned
def transfer_bux(v, username):
	abort(404) # disable entirely pending possible future use of coins

	receiver = g.db.query(User).filter_by(username=username).one_or_none()

	if not receiver: abort(404, "That user doesn't exist.")

	if receiver.id != v.id:
		amount = request.values.get("amount", "").strip()
		amount = int(amount) if amount.isdigit() else None

		if not amount or amount < 0: abort(400, "Invalid amount of marseybux.")
		if v.procoins < amount: abort(400, "You don't have enough marseybux")
		if amount < 100: abort(400, "You have to gift at least 100 marseybux.")

		log_message = f"@{v.username} has transferred {amount} Marseybux to @{receiver.username}"
		send_repeatable_notification(GIFT_NOTIF_ID, log_message)

		receiver.procoins += amount
		v.procoins -= amount
		send_repeatable_notification(receiver.id, f":marseycapitalistmanlet: @{v.username} has gifted you {amount} marseybux!")
		g.db.add(receiver)
		g.db.add(v)

		g.db.commit()
		return {"message": f"{amount} marseybux transferred!"}, 200

	return {"message": "You can't transfer marseybux to yourself!"}, 400


@app.get("/leaderboard")
@admin_level_required(2)
def leaderboard(v:User):
	users:Query = g.db.query(User)
	if not v.can_see_shadowbanned:
		users = users.filter(User.shadowbanned == None)

	coins = SimpleLeaderboard(v, LeaderboardMeta("Coins", "coins", "coins", "Coins", None), g.db, users, User.coins)
	subscribers = SimpleLeaderboard(v, LeaderboardMeta("Followers", "followers", "followers", "Followers", "followers"), g.db, users, User.stored_subscriber_count)
	posts = SimpleLeaderboard(v, LeaderboardMeta("Posts", "post count", "posts", "Posts", ""), g.db, users, User.post_count)
	comments = SimpleLeaderboard(v, LeaderboardMeta("Comments", "comment count", "comments", "Comments", "comments"), g.db, users, User.comment_count)
	received_awards = SimpleLeaderboard(v, LeaderboardMeta("Awards", "received awards", "awards", "Awards", None), g.db, users, User.received_award_count)
	coins_spent = SimpleLeaderboard(v, LeaderboardMeta("Spent in shop", "coins spent in shop", "spent", "Coins", None), g.db, users, User.coins_spent)
	truescore = SimpleLeaderboard(v, LeaderboardMeta("Truescore", "truescore", "truescore", "Truescore", None), g.db, users, User.truecoins)
	badges = BadgeMarseyLeaderboard(v, LeaderboardMeta("Badges", "badges", "badges", "Badges", None), g.db, Badge.user_id)
	blocks = UserBlockLeaderboard(v, LeaderboardMeta("Blocked", "most blocked", "blocked", "Blocked By", "blockers"), g.db, UserBlock.target_id)

	received_downvotes_lb = None
	given_upvotes_lb = None

	try:
		pos9 = [x[0].id for x in lb_received_downvotes].index(v.id)
		pos9 = (pos9+1, lb_received_downvotes[pos9][1])
	except: pos9 = (len(lb_received_downvotes)+1, 0)

	try:
		pos13 = [x[0].id for x in lb_given_upvotes].index(v.id)
		pos13 = (pos13+1, lb_given_upvotes[pos13][1])
	except: pos13 = (len(lb_given_upvotes)+1, 0)

	leaderboards = [coins, coins_spent, truescore, subscribers, posts, comments, received_awards, badges, blocks]

	return render_template("leaderboard.html", v=v, leaderboards=leaderboards, users9=lb_received_downvotes, pos9=pos9, users13=lb_given_upvotes, pos13=pos13)

@app.get("/@<username>/css")
def get_css(username):
	user = get_user(username)
	resp=make_response(user.css or "")
	resp.headers.add("Content-Type", "text/css")
	return resp

@app.get("/@<username>/profilecss")
def get_profilecss(username):
	user = get_user(username)
	if user.profilecss: profilecss = user.profilecss
	else: profilecss = ""
	resp=make_response(profilecss)
	resp.headers.add("Content-Type", "text/css")
	return resp

@app.post("/subscribe/<post_id>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def subscribe(v, post_id):
	new_sub = Subscription(user_id=v.id, submission_id=post_id)
	g.db.add(new_sub)
	g.db.commit()
	return {"message": "Post subscribed!"}
	
@app.post("/unsubscribe/<post_id>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def unsubscribe(v, post_id):
	sub=g.db.query(Subscription).filter_by(user_id=v.id, submission_id=post_id).one_or_none()
	if sub:
		g.db.delete(sub)
		g.db.commit()
	return {"message": "Post unsubscribed!"}

@app.get("/report_bugs")
@auth_required
def reportbugs(v):
	return redirect(f'/post/{BUG_THREAD}')

@app.post("/@<username>/message")
@limiter.limit("1/second;10/minute;20/hour;50/day")
@auth_required
def message2(v, username):
	if v.is_suspended_permanently:
		abort(403, "You have been permabanned and cannot send messages; " + \
			"contact modmail if you think this decision was incorrect.")

	user = get_user(username, v=v, include_blocks=True)
	if hasattr(user, 'is_blocking') and user.is_blocking: abort(403, "You're blocking this user.")

	if v.admin_level <= 1 and hasattr(user, 'is_blocked') and user.is_blocked:
		abort(403, "This user is blocking you.")

	message = request.values.get("message", "").strip()[:10000].strip()

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
						  body_html=body_html
						  )
	g.db.add(c)

	g.db.flush()

	c.top_comment_id = c.id

	notif = g.db.query(Notification).filter_by(comment_id=c.id, user_id=user.id).one_or_none()
	if not notif:
		notif = Notification(comment_id=c.id, user_id=user.id)
		g.db.add(notif)

	g.db.commit()

	if PUSHER_ID != 'blahblahblah' and not v.shadowbanned:
		if len(message) > 500: notifbody = message[:500] + '...'
		else: notifbody = message

		try: gevent.spawn(pusher_thread2, f'{request.host}{user.id}', notifbody, v.username)
		except: pass

	return {"message": "Message sent!"}


@app.post("/reply")
@limiter.limit("1/second;6/minute;50/hour;200/day")
@auth_required
def messagereply(v):

	message = request.values.get("body", "").strip()[:10000].strip()

	if not message and not request.files.get("file"): abort(400, "Message is empty!")

	id = int(request.values.get("parent_id"))
	parent = get_comment(id, v=v)
	user_id = parent.author.id

	if parent.sentto == 2: user_id = None
	elif v.id == user_id: user_id = parent.sentto

	body_html = sanitize(message)

	if parent.sentto == 2 and request.files.get("file") and request.headers.get("cf-ipcountry") != "T1":
		file=request.files["file"]
		if file.content_type.startswith('image/'):
			name = f'/images/{time.time()}'.replace('.','') + '.webp'
			file.save(name)
			url = process_image(name)
			body_html += f'<img data-bs-target="#expandImageModal" data-bs-toggle="modal" onclick="expandDesktopImage(this.src)" class="img" src="{url}" loading="lazy">'
		elif file.content_type.startswith('video/'):
			file.save("video.mp4")
			with open("video.mp4", 'rb') as f:
				try: req = requests.request("POST", "https://api.imgur.com/3/upload", headers={'Authorization': f'Client-ID {IMGUR_KEY}'}, files=[('video', f)], timeout=5).json()['data']
				except requests.Timeout: abort(500, "Video upload timed out, please try again!")
				try: url = req['link']
				except:
					error = req['error']
					if error == 'File exceeds max duration': error += ' (60 seconds)'
					abort(400, error)
			if url.endswith('.'): url += 'mp4'
			body_html += f"<p>{url}</p>"
		else: abort(400, "Image/Video files only")


	c = Comment(author_id=v.id,
							parent_submission=None,
							parent_comment_id=id,
							top_comment_id=parent.top_comment_id,
							level=parent.level + 1,
							sentto=user_id,
							body_html=body_html,
							)
	g.db.add(c)
	g.db.flush()

	if user_id and user_id != v.id and user_id != 2:
		notif = g.db.query(Notification).filter_by(comment_id=c.id, user_id=user_id).one_or_none()
		if not notif:
			notif = Notification(comment_id=c.id, user_id=user_id)
			g.db.add(notif)
			ids = [c.top_comment.id] + [x.id for x in c.top_comment.replies_ignoring_shadowbans]
			notifications = g.db.query(Notification).filter(Notification.comment_id.in_(ids), Notification.user_id == user_id)
			for n in notifications:
				g.db.delete(n)

		if PUSHER_ID != 'blahblahblah' and not v.shadowbanned:
			if len(message) > 500: notifbody = message[:500] + '...'
			else: notifbody = message
			
			beams_client.publish_to_interests(
				interests=[f'{request.host}{user_id}'],
				publish_body={
					'web': {
						'notification': {
							'title': f'New message from @{v.username}',
							'body': notifbody,
							'deep_link': f'{SITE_FULL}/notifications?messages=true',
							'icon': SITE_FULL + assetcache_path(f'images/{SITE_ID}/icon.webp'),
						}
					},
					'fcm': {
						'notification': {
							'title': f'New message from @{v.username}',
							'body': notifbody,
						},
						'data': {
							'url': '/notifications?messages=true',
						}
					}
				},
			)


	if c.top_comment.sentto == 2:
		admins = g.db.query(User).filter(User.admin_level > 2, User.id != v.id).all()
		for admin in admins:
			notif = Notification(comment_id=c.id, user_id=admin.id)
			g.db.add(notif)

		ids = [c.top_comment.id] + [x.id for x in c.top_comment.replies_ignoring_shadowbans]
		notifications = g.db.query(Notification).filter(Notification.comment_id.in_(ids))
		for n in notifications:
			g.db.delete(n)

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

	try: f = send_file(mem, mimetype="image/png", as_attachment=False)
	except:
		print('/2faqr/<secret>', flush=True)
		abort(404)
	return f


@app.get("/is_available/<name>")
def api_is_available(name):

	name=name.strip()

	if len(name)<3 or len(name)>25:
		return {name:False}
		
	name2 = sql_ilike_clean(name)

	x= g.db.query(User).filter(
		or_(
			User.username.ilike(name2),
			User.original_username.ilike(name2)
			)
		).one_or_none()

	if x:
		return {name: False}
	else:
		return {name: True}

@app.get("/id/<id>")
@auth_desired
def user_id(v, id):
	user = get_account(id)
	return redirect(user.url)
		
@app.get("/u/<username>")
@auth_desired
def redditor_moment_redirect(v, username):
	return redirect(f"/@{username}")

@app.get("/@<username>/followers")
@auth_desired
def followers(v, username):
	u = get_user(username, v=v)
	users = g.db.query(User).join(Follow, Follow.target_id == u.id).filter(Follow.user_id == User.id).order_by(Follow.created_utc).all()
	return render_template("followers.html", v=v, u=u, users=users)

@app.get("/@<username>/following")
@auth_desired
def following(v, username):
	u = get_user(username, v=v)
	users = g.db.query(User).join(Follow, Follow.user_id == u.id).filter(Follow.target_id == User.id).order_by(Follow.created_utc).all()
	return render_template("following.html", v=v, u=u, users=users)

@app.get("/views")
@auth_required
def visitors(v):
	if v.admin_level < 2 and not v.patron: return render_template("errors/patron.html", v=v)
	viewers=sorted(v.viewers, key = lambda x: x.last_view_utc, reverse=True)
	return render_template("viewers.html", v=v, viewers=viewers)


@app.get("/@<username>")
@auth_desired
def u_username(username, v=None):
	u = get_user(username, v=v, include_blocks=True)

	if username != u.username:
		return redirect(SITE_FULL + request.full_path.replace(username, u.username)[:-1])

	if u.reserved:
		if request.headers.get("Authorization") or request.headers.get("xhr"): abort(403, f"That username is reserved for: {u.reserved}")
		return render_template("userpage_reserved.html", u=u, v=v)

	if v and v.id != u.id and (u.patron or u.admin_level > 1):
		view = g.db.query(ViewerRelationship).filter_by(viewer_id=v.id, user_id=u.id).one_or_none()

		if view: view.last_view_utc = int(time.time())
		else: view = ViewerRelationship(viewer_id=v.id, user_id=u.id)

		g.db.add(view)
		g.db.commit()

		
	if u.is_private and (not v or (v.id != u.id and v.admin_level < 2)):
		if request.headers.get("Authorization") or request.headers.get("xhr"): abort(403, "That userpage is private")
		return render_template("userpage_private.html", u=u, v=v)

	
	if v and hasattr(u, 'is_blocking') and u.is_blocking:
		if request.headers.get("Authorization") or request.headers.get("xhr"): abort(403, f"You are blocking @{u.username}.")
		return render_template("userpage_blocking.html", u=u, v=v)

	sort = request.values.get("sort", "new")
	t = request.values.get("t", "all")
	try: page = max(int(request.values.get("page", 1)), 1)
	except: page = 1

	ids = u.userpagelisting(site=SITE, v=v, page=page, sort=sort, t=t)

	next_exists = (len(ids) > 25)
	ids = ids[:25]

	if page == 1:
		sticky = []
		sticky = g.db.query(Submission).filter_by(is_pinned=True, author_id=u.id).all()
		if sticky:
			for p in sticky:
				ids = [p.id] + ids

	listing = get_posts(ids, v=v, eager=True)

	if u.unban_utc:
		if request.headers.get("Authorization"): {"data": [x.json for x in listing]}
		return render_template("userpage.html",
												unban=u.unban_string,
												u=u,
												v=v,
												listing=listing,
												page=page,
												sort=sort,
												t=t,
												next_exists=next_exists,
												is_following=(v and u.has_follower(v)))



	if request.headers.get("Authorization"): return {"data": [x.json for x in listing]}
	return render_template("userpage.html",
									u=u,
									v=v,
									listing=listing,
									page=page,
									sort=sort,
									t=t,
									next_exists=next_exists,
									is_following=(v and u.has_follower(v)))


@app.get("/@<username>/comments")
@auth_desired
def u_username_comments(username, v=None):
	user = get_user(username, v=v, include_blocks=True)

	if username != user.username: return redirect(f'/@{user.username}/comments')
	u = user

	if u.reserved:
		if request.headers.get("Authorization") or request.headers.get("xhr"): abort(403, f"That username is reserved for: {u.reserved}")
		return render_template("userpage_reserved.html",
												u=u,
												v=v)


	if u.is_private and (not v or (v.id != u.id and v.admin_level < 2)):
		if request.headers.get("Authorization") or request.headers.get("xhr"): abort(403, "That userpage is private")
		return render_template("userpage_private.html", u=u, v=v)

	if v and hasattr(u, 'is_blocking') and u.is_blocking:
		if request.headers.get("Authorization") or request.headers.get("xhr"): abort(403, f"You are blocking @{u.username}.")
		return render_template("userpage_blocking.html", u=u, v=v)

	try: page = max(int(request.values.get("page", "1")), 1)
	except: page = 1
	
	sort=request.values.get("sort","new")
	t=request.values.get("t","all")


	comments = g.db.query(Comment.id).filter(Comment.author_id == u.id, Comment.parent_submission != None)

	if not v or (v.id != u.id and v.admin_level < 2):
		comments = comments.filter(
				Comment.deleted_utc == 0,
				Comment.is_banned == False,
				Comment.ghost == False,
				(Comment.filter_state != 'filtered') & (Comment.filter_state != 'removed')
				)

	comments = apply_time_filter(comments, t, Comment)
	comments = sort_objects(comments, sort, Comment)

	comments = comments.offset(25 * (page - 1)).limit(26).all()
	ids = [x.id for x in comments]

	next_exists = (len(ids) > 25)
	ids = ids[:25]

	listing = get_comments(ids, v=v)

	is_following = (v and user.has_follower(v))

	if request.headers.get("Authorization"): return {"data": [c.json for c in listing]}
	return render_template("userpage_comments.html", u=user, v=v, listing=listing, page=page, sort=sort, t=t,next_exists=next_exists, is_following=is_following, standalone=True)


@app.get("/@<username>/info")
@auth_required
def u_username_info(username, v=None):
	user = get_user(username, v=v, include_blocks=True)

	if hasattr(user, 'is_blocking') and user.is_blocking:
		abort(401, "You're blocking this user.")
	elif hasattr(user, 'is_blocked') and user.is_blocked:
		abort(403, "This user is blocking you.")

	return user.json

@app.get("/<id>/info")
@auth_required
def u_user_id_info(id, v=None):
	user = get_account(id, v=v, include_blocks=True)

	if hasattr(user, 'is_blocking') and user.is_blocking:
		abort(401, "You're blocking this user.")
	elif hasattr(user, 'is_blocked') and user.is_blocked:
		abort(403, "This user is blocking you.")

	return user.json

@app.post("/follow/<username>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def follow_user(username, v):

	target = get_user(username)

	if target.id==v.id: abort(400, "You can't follow yourself!")

	if g.db.query(Follow).filter_by(user_id=v.id, target_id=target.id).one_or_none(): return {"message": "User followed!"}

	new_follow = Follow(user_id=v.id, target_id=target.id)
	g.db.add(new_follow)

	g.db.flush()
	target.stored_subscriber_count = g.db.query(Follow.target_id).filter_by(target_id=target.id).count()
	g.db.add(target)

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

	send_repeatable_notification(target.id, f"@{v.username} has removed your follow!")

	g.db.commit()

	return {"message": "Follower removed!"}

from urllib.parse import urlparse
import re

@app.get("/pp/<id>")
@app.get("/uid/<id>/pic")
@app.get("/uid/<id>/pic/profile")
@limiter.exempt
def user_profile_uid(v, id):
	try: id = int(id)
	except:
		try: id = int(id, 36)
		except: abort(404)

	name = f"/pp/{id}"
	path = cache.get(name)
	tout = 5 * 60 # 5 min

	# if the path isn't cached then make it
	if not path:
		user = get_account(id)
		path = urlparse(user.profile_url).path
		cache.set(name,path,timeout=tout)

	# if not found, search relative to the root
	if not os.path.exists(path):
		path = os.path.join(app.root_path,path.lstrip('/'))
		cache.set(name,path,timeout=tout)

	# if not found, fail
	if not os.path.exists(path):
		cache.set(name,None)
		abort(404)

	return send_file(path)

@app.get("/@<username>/pic")
@limiter.exempt
@auth_required
def user_profile_name(v, username):

	name = f"/@{username}/pic"
	path = cache.get(name)
	tout = 5 * 60 # 5 min

	# if the path isn't cached then make it
	if not path:
		user = get_user(username)
		path = urlparse(user.profile_url).path
		cache.set(name,path,timeout=tout)

	# if not found, search relative to the root
	if not os.path.exists(path):
		path = os.path.join(app.root_path,path.lstrip('/'))
		cache.set(name,path,timeout=tout)

	# if not found, fail
	if not os.path.exists(path):
		cache.set(name,None)
		abort(404)

	return send_file(path)

@app.get("/@<username>/saved/posts")
@auth_required
def saved_posts(v, username):

	page=int(request.values.get("page",1))

	ids=v.saved_idlist(page=page)

	next_exists=len(ids)>25

	ids=ids[:25]

	listing = get_posts(ids, v=v, eager=True)

	if request.headers.get("Authorization"): return {"data": [x.json for x in listing]}
	return render_template("userpage.html",
											u=v,
											v=v,
											listing=listing,
											page=page,
											next_exists=next_exists,
											)


@app.get("/@<username>/saved/comments")
@auth_required
def saved_comments(v, username):

	page=int(request.values.get("page",1))

	ids=v.saved_comment_idlist(page=page)

	next_exists=len(ids) > 25

	ids=ids[:25]

	listing = get_comments(ids, v=v)


	if request.headers.get("Authorization"): return {"data": [x.json for x in listing]}
	return render_template("userpage_comments.html",
											u=v,
											v=v,
											listing=listing,
											page=page,
											next_exists=next_exists,
											standalone=True)


@app.post("/fp/<fp>")
@auth_required
def fp(v, fp):
	v.fp = fp
	users = g.db.query(User).filter(User.fp == fp, User.id != v.id).all()
	if users: print(f'{v.username}: fp {v.fp}')
	if v.email and v.is_activated:
		alts = g.db.query(User).filter(User.email == v.email, User.is_activated, User.id != v.id).all()
		if alts:
			print(f'{v.username}: email {v.email}')
			users += alts
	for u in users:
		li = [v.id, u.id]
		existing = g.db.query(Alt).filter(Alt.user1.in_(li), Alt.user2.in_(li)).one_or_none()
		if existing: continue
		new_alt = Alt(user1=v.id, user2=u.id)
		g.db.add(new_alt)
		g.db.flush()
		print(v.username + ' + ' + u.username)
	g.db.add(v)
	g.db.commit()
	return '', 204
