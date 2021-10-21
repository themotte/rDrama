from files.__main__ import app, limiter
from files.helpers.wrappers import *
from files.helpers.alerts import *
from files.helpers.get import *
from files.helpers.const import *
from files.classes.award import *
from .front import frontlist
from flask import g, request

AWARDS2 = {
	"ban": {
		"kind": "ban",
		"title": "1-Day Ban",
		"description": "Bans the author for a day.",
		"icon": "fas fa-gavel",
		"color": "text-danger",
		"price": 3000
	},
	"fireflies": {
		"kind": "fireflies",
		"title": "Fireflies",
		"description": "Puts fireflies on the post.",
		"icon": "fas fa-sparkles",
		"color": "text-warning",
		"price": 500
	},
	"shit": {
		"kind": "shit",
		"title": "Shit",
		"description": "Makes flies swarm a post.",
		"icon": "fas fa-poop",
		"color": "text-black-50",
		"price": 500
	},
}

@app.get("/shop")
@app.get("/settings/shop")
@auth_required
def shop(v):
	if site_name == "Drama":
		AWARDS = {
			"ban": {
				"kind": "ban",
				"title": "1-Day Ban",
				"description": "Bans the author for a day.",
				"icon": "fas fa-gavel",
				"color": "text-danger",
				"price": 3000
			},
			"unban": {
				"kind": "unban",
				"title": "1-Day Unban",
				"description": "Removes 1 day from the ban duration of the recipient.",
				"icon": "fas fa-gavel",
				"color": "text-success",
				"price": 3500
			},
			"grass": {
				"kind": "grass",
				"title": "Grass",
				"description": "Ban the author permanently (must provide a timestamped picture of them touching grass to the admins to get unbanned)",
				"icon": "fas fa-seedling",
				"color": "text-success",
				"price": 10000
			},
			"shit": {
				"kind": "shit",
				"title": "Shit",
				"description": "Makes flies swarm a post.",
				"icon": "fas fa-poop",
				"color": "text-black-50",
				"price": 500
			},
			"fireflies": {
				"kind": "fireflies",
				"title": "Fireflies",
				"description": "Puts fireflies on the post.",
				"icon": "fas fa-sparkles",
				"color": "text-warning",
				"price": 500
			},
			"train": {
				"kind": "train",
				"title": "Train",
				"description": "Summons a train on the post.",
				"icon": "fas fa-train",
				"color": "text-pink",
				"price": 500
			},
			"pin": {
				"kind": "pin",
				"title": "1-Hour Pin",
				"description": "Pins the post.",
				"icon": "fas fa-thumbtack fa-rotate--45",
				"color": "text-warning",
				"price": 750
			},
			"unpin": {
				"kind": "unpin",
				"title": "1-Hour Unpin",
				"description": "Removes 1 hour from the pin duration of the post.",
				"icon": "fas fa-thumbtack fa-rotate--45",
				"color": "text-black",
				"price": 1000
			},
			"agendaposter": {
				"kind": "agendaposter",
				"title": "Agendaposter",
				"description": "Force the agendaposter theme on the author for 24 hours.",
				"icon": "fas fa-snooze",
				"color": "text-purple",
				"price": 2000
			},
		}
	else:
		AWARDS = {
			"shit": {
				"kind": "shit",
				"title": "Shit",
				"description": "Makes flies swarm a post.",
				"icon": "fas fa-poop",
				"color": "text-black-50",
				"price": 500
			},
			"fireflies": {
				"kind": "fireflies",
				"title": "Fireflies",
				"description": "Puts fireflies on the post.",
				"icon": "fas fa-sparkles",
				"color": "text-warning",
				"price": 500
			},
			"train": {
				"kind": "train",
				"title": "Train",
				"description": "Summons a train on the post.",
				"icon": "fas fa-train",
				"color": "text-pink",
				"price": 50
			},
			"pin": {
				"kind": "pin",
				"title": "1-Hour Pin",
				"description": "Pins the post.",
				"icon": "fas fa-thumbtack fa-rotate--45",
				"color": "text-warning",
				"price": 750
			},
			"unpin": {
				"kind": "unpin",
				"title": "1-Hour Unpin",
				"description": "Removes 1 hour from the pin duration of the post.",
				"icon": "fas fa-thumbtack fa-rotate--45",
				"color": "text-black",
				"price": 1000
			},
		}

	query = g.db.query(
	User.id, User.username, User.patron, User.namecolor,
	AwardRelationship.kind.label('last_award_kind'), func.count(AwardRelationship.id).label('last_award_count')
	).filter(AwardRelationship.submission_id==None, AwardRelationship.comment_id==None, User.patron > 0) \
	.group_by(User.username, User.patron, User.id, User.namecolor, AwardRelationship.kind) \
	.order_by(User.patron.desc(), AwardRelationship.kind.desc()) \
	.join(User).filter(User.id == v.id).all()

	owned = []
	for row in (r._asdict() for r in query):
		kind = row['last_award_kind']
		if kind in AWARDS.keys():
			award = AWARDS[kind]
			award["owned_num"] = row['last_award_count']
			owned.append(award)

	if v.patron:
		for val in AWARDS.values():
			if v.patron == 1: val["price"] = int(val["price"]*0.90)
			elif v.patron == 2: val["price"] = int(val["price"]*0.85)
			elif v.patron == 3: val["price"] = int(val["price"]*0.80)
			elif v.patron == 4: val["price"] = int(val["price"]*0.75)
			else: val["price"] = int(val["price"]*0.70)

	sales = g.db.query(Vote.id).count() + g.db.query(CommentVote.id).count() - g.db.query(func.sum(User.coins)).scalar()
	return render_template("shop.html", owned=owned, awards=list(AWARDS.values()), v=v, sales=sales)


@app.post("/buy/<award>")
@auth_required
def buy(v, award):
	if site_name == "Drama":
		AWARDS = {
			"ban": {
				"kind": "ban",
				"title": "1-Day Ban",
				"description": "Bans the author for a day.",
				"icon": "fas fa-gavel",
				"color": "text-danger",
				"price": 3000
			},
			"unban": {
				"kind": "unban",
				"title": "1-Day Unban",
				"description": "Removes 1 day from the ban duration of the recipient.",
				"icon": "fas fa-gavel",
				"color": "text-success",
				"price": 3500
			},
			"grass": {
				"kind": "grass",
				"title": "Grass",
				"description": "Ban the author permanently (must provide a timestamped picture of them touching grass to the admins to get unbanned)",
				"icon": "fas fa-seedling",
				"color": "text-success",
				"price": 10000
			},
			"shit": {
				"kind": "shit",
				"title": "Shit",
				"description": "Makes flies swarm a post.",
				"icon": "fas fa-poop",
				"color": "text-black-50",
				"price": 500
			},
			"fireflies": {
				"kind": "fireflies",
				"title": "Fireflies",
				"description": "Puts fireflies on the post.",
				"icon": "fas fa-sparkles",
				"color": "text-warning",
				"price": 500
			},
			"train": {
				"kind": "train",
				"title": "Train",
				"description": "Summons a train on the post.",
				"icon": "fas fa-train",
				"color": "text-pink",
				"price": 500
			},
			"pin": {
				"kind": "pin",
				"title": "1-Hour Pin",
				"description": "Pins the post.",
				"icon": "fas fa-thumbtack fa-rotate--45",
				"color": "text-warning",
				"price": 750
			},
			"unpin": {
				"kind": "unpin",
				"title": "1-Hour Unpin",
				"description": "Removes 1 hour from the pin duration of the post.",
				"icon": "fas fa-thumbtack fa-rotate--45",
				"color": "text-black",
				"price": 1000
			},
			"agendaposter": {
				"kind": "agendaposter",
				"title": "Agendaposter",
				"description": "Force the agendaposter theme on the author for 24 hours.",
				"icon": "fas fa-snooze",
				"color": "text-purple",
				"price": 2000
			},
		}
	else:
		AWARDS = {
			"shit": {
				"kind": "shit",
				"title": "Shit",
				"description": "Makes flies swarm a post.",
				"icon": "fas fa-poop",
				"color": "text-black-50",
				"price": 500
			},
			"fireflies": {
				"kind": "fireflies",
				"title": "Fireflies",
				"description": "Puts fireflies on the post.",
				"icon": "fas fa-sparkles",
				"color": "text-warning",
				"price": 500
			},
			"train": {
				"kind": "train",
				"title": "Train",
				"description": "Summons a train on the post.",
				"icon": "fas fa-train",
				"color": "text-pink",
				"price": 500
			},
			"pin": {
				"kind": "pin",
				"title": "1-Hour Pin",
				"description": "Pins the post.",
				"icon": "fas fa-thumbtack fa-rotate--45",
				"color": "text-warning",
				"price": 750
			},
			"unpin": {
				"kind": "unpin",
				"title": "1-Hour Unpin",
				"description": "Removes 1 hour from the pin duration of the post.",
				"icon": "fas fa-thumbtack fa-rotate--45",
				"color": "text-black",
				"price": 1000
			},
		}

	if award not in AWARDS: abort(400)
	price = AWARDS[award]["price"]
	if v.patron:
		if v.patron == 1: price = int(price*0.90)
		elif v.patron == 2: price = int(price*0.85)
		elif v.patron == 3: price = int(price*0.80)
		elif v.patron == 4: price = int(price*0.75)
		else: price = int(price*0.70)

	if v.coins < price: return {"error": "Not enough coins."}, 400
	v.coins -= price
	v.coins_spent += price
	g.db.add(v)

	g.db.flush()
	thing = g.db.query(AwardRelationship).order_by(AwardRelationship.id.desc()).first().id
	thing += 1

	award = AwardRelationship(id=thing, user_id=v.id, kind=award)
	g.db.add(award)

	g.db.commit()

	return {"message": "Award bought!"}


@app.post("/post/<pid>/awards")
@limiter.limit("1/second")
@auth_required
def award_post(pid, v):

	if v.is_suspended and v.unban_utc == 0: return {"error": "forbidden."}, 403

	kind = request.values.get("kind", "").strip()
	
	if kind not in AWARDS:
		return {"error": "That award doesn't exist."}, 404

	post_award = g.db.query(AwardRelationship).options(lazyload('*')).filter(
		and_(
			AwardRelationship.kind == kind,
			AwardRelationship.user_id == v.id,
			AwardRelationship.submission_id == None,
			AwardRelationship.comment_id == None
		)
	).first()

	if not post_award:
		return {"error": "You don't have that award."}, 404

	post = g.db.query(Submission).options(lazyload('*')).filter_by(id=pid).first()

	if not post:
		return {"error": "That post doesn't exist."}, 404

	existing_award = g.db.query(AwardRelationship).options(lazyload('*')).filter(
		and_(
			AwardRelationship.submission_id == post.id,
			AwardRelationship.user_id == v.id,
			AwardRelationship.kind == kind
		)
	).first()

	post_award.submission_id = post.id
	g.db.add(post_award)

	msg = f"@{v.username} has given your [post]({post.permalink}) the {AWARDS[kind]['title']} Award!"

	note = request.values.get("note", "").strip()
	if note: msg += f"\n\n> {note}"

	send_notification(NOTIFICATIONS_ACCOUNT, post.author, msg)

	author = post.author
	if kind == "ban":
		link = f"[this post]({post.permalink})"

		if not author.is_suspended:
			author.ban(reason=f"1-Day ban award used by @{v.username} on /post/{post.id}", days=1)
			send_notification(NOTIFICATIONS_ACCOUNT, author, f"Your account has been suspended for a day for {link}. It sucked and you should feel bad.")
		elif author.unban_utc > 0:
			author.unban_utc += 24*60*60
			send_notification(NOTIFICATIONS_ACCOUNT, author, f"Your account has been suspended for yet another day for {link}. Seriously man?")
	elif kind == "unban":
		if not author.is_suspended or not author.unban_utc or time.time() > author.unban_utc: abort(403)

		if author.unban_utc - time.time() > 86400:
			author.unban_utc -= 86400
			send_notification(NOTIFICATIONS_ACCOUNT, author, f"Your ban duration has been reduced by 1 day!")
		else:
			author.unban_utc = 0
			author.is_banned = 0
			author.ban_evade = 0
			send_notification(NOTIFICATIONS_ACCOUNT, author, f"You have been unbanned!")
	elif kind == "grass":
		author.is_banned = AUTOJANNY_ACCOUNT
		author.ban_reason = f"grass award used by @{v.username} on /post/{post.id}"
		link = f"[this post]({post.permalink})"
		send_notification(NOTIFICATIONS_ACCOUNT, author, f"Your account has been suspended permanently for {link}. You must [provide the admins](/contact) a timestamped picture of you touching grass to get unbanned!")
	elif kind == "pin":
		if post.stickied and post.stickied.startswith("t:"): t = int(post.stickied[2:]) + 3600
		else: t = int(time.time()) + 3600
		post.stickied = f"t:{t}"
		g.db.add(post)
		cache.delete_memoized(frontlist)
	elif kind == "unpin":
		if not (post.stickied and post.stickied.startswith("t:")): abort(403)
		t = int(post.stickied[2:]) - 3600
		if time.time() > t:
			post.stickied = None
			cache.delete_memoized(frontlist)
		else: post.stickied = f"t:{t}"
		g.db.add(post)
	elif kind == "agendaposter" and not (author.agendaposter and author.agendaposter_expires_utc == 0):
		if author.agendaposter_expires_utc and time.time() < author.agendaposter_expires_utc: author.agendaposter_expires_utc += 86400
		else: author.agendaposter_expires_utc = time.time() + 86400
		
		author.agendaposter = True
		if not author.has_badge(26):
			badge = Badge(user_id=author.id, badge_id=26)
			g.db.add(badge)

	post.author.received_award_count += 1
	g.db.add(post.author)

	g.db.commit()
	if request.referrer and len(request.referrer) > 1: return redirect(request.referrer)
	else: return redirect("/")


@app.post("/comment/<cid>/awards")
@limiter.limit("1/second")
@auth_required
def award_comment(cid, v):

	if v.is_suspended and v.unban_utc == 0: return {"error": "forbidden"}, 403

	kind = request.values.get("kind", "").strip()

	if kind not in AWARDS:
		return {"error": "That award doesn't exist."}, 404

	comment_award = g.db.query(AwardRelationship).options(lazyload('*')).filter(
		and_(
			AwardRelationship.kind == kind,
			AwardRelationship.user_id == v.id,
			AwardRelationship.submission_id == None,
			AwardRelationship.comment_id == None
		)
	).first()

	if not comment_award:
		return {"error": "You don't have that award."}, 404

	c = g.db.query(Comment).options(lazyload('*')).filter_by(id=cid).first()

	if not c:
		return {"error": "That comment doesn't exist."}, 404

	existing_award = g.db.query(AwardRelationship).options(lazyload('*')).filter(
		and_(
			AwardRelationship.comment_id == c.id,
			AwardRelationship.user_id == v.id,
			AwardRelationship.kind == kind
		)
	).first()

	comment_award.comment_id = c.id
	g.db.add(comment_award)

	msg = f"@{v.username} has given your [comment]({c.permalink}) the {AWARDS[kind]['title']} Award!"

	note = request.values.get("note", "").strip()
	if note: msg += f"\n\n> {note}"

	send_notification(NOTIFICATIONS_ACCOUNT, c.author, msg)
	author = c.author

	if kind == "ban":
		link = f"[this comment]({c.permalink})"

		if not author.is_suspended:
			author.ban(reason=f"1-Day ban award used by @{v.username} on /comment/{c.id}", days=1)
			send_notification(NOTIFICATIONS_ACCOUNT, author, f"Your account has been suspended for a day for {link}. It sucked and you should feel bad.")
		elif author.unban_utc > 0:
			author.unban_utc += 24*60*60
			send_notification(NOTIFICATIONS_ACCOUNT, author, f"Your account has been suspended for yet another day for {link}. Seriously man?")
	elif kind == "unban":
		if not author.is_suspended or not author.unban_utc or time.time() > author.unban_utc: abort(403)

		if author.unban_utc - time.time() > 86400:
			author.unban_utc -= 86400
			send_notification(NOTIFICATIONS_ACCOUNT, author, f"Your ban duration has been reduced by 1 day!")
		else:
			author.unban_utc = 0
			author.is_banned = 0
			author.ban_evade = 0
			send_notification(NOTIFICATIONS_ACCOUNT, author, f"You have been unbanned!")
	elif kind == "grass":
		author.is_banned = AUTOJANNY_ACCOUNT
		author.ban_reason = f"grass award used by @{v.username} on /comment/{c.id}"
		link = f"[this comment]({c.permalink})"
		send_notification(NOTIFICATIONS_ACCOUNT, author, f"Your account has been suspended permanently for {link}. You must [provide the admins](/contact) a timestamped picture of you touching grass to get unbanned!")
	elif kind == "pin":
		if c.is_pinned and c.is_pinned.startswith("t:"): t = int(c.is_pinned[2:]) + 3600
		else: t = int(time.time()) + 3600
		c.is_pinned = f"t:{t}"
		g.db.add(c)
	elif kind == "unpin":
		if not (c.is_pinned and c.is_pinned.startswith("t:")): abort(403)
		t = int(c.is_pinned[2:]) - 3600
		if time.time() > t: c.is_pinned = None
		else: c.is_pinned = f"t:{t}"
		g.db.add(c)
	elif kind == "agendaposter" and not (author.agendaposter and author.agendaposter_expires_utc == 0):
		if author.agendaposter_expires_utc and time.time() < author.agendaposter_expires_utc: author.agendaposter_expires_utc += 86400
		else: author.agendaposter_expires_utc = time.time() + 86400
		
		author.agendaposter = True
		if not author.has_badge(26):
			badge = Badge(user_id=author.id, badge_id=26)
			g.db.add(badge)

	c.author.received_award_count += 1
	g.db.add(c.author)

	g.db.commit()
	if request.referrer and len(request.referrer) > 1: return redirect(request.referrer)
	else: return redirect("/")

@app.get("/admin/awards")
@admin_level_required(6)
def admin_userawards_get(v):

	if v.username == "Aevann": return render_template("admin/awards.html", awards=list(AWARDS.values()), v=v)
	return render_template("admin/awards.html", awards=list(AWARDS2.values()), v=v)

@app.post("/admin/awards")
@limiter.limit("1/second")
@auth_required
@validate_formkey
def admin_userawards_post(v):

	if v.admin_level < 6:
		abort(403)

	try: u = request.values.get("username").strip()
	except: abort(404)

	u = get_user(u, graceful=False, v=v)

	notify_awards = {}

	latest = g.db.query(AwardRelationship).order_by(AwardRelationship.id.desc()).first()
	thing = latest.id

	for key, value in request.values.items():
		if key not in AWARDS: continue

		if value:

			if int(value) > 0:
				notify_awards[key] = int(value)

			for x in range(int(value)):
				thing += 1

				award = AwardRelationship(
					id=thing,
					user_id=u.id,
					kind=key
				)

				g.db.add(award)

	text = "You were given the following awards:\n\n"

	for key, value in notify_awards.items():
		text += f" - **{value}** {AWARDS[key]['title']} {'Awards' if value != 1 else 'Award'}\n"

	send_notification(NOTIFICATIONS_ACCOUNT, u, text)

	g.db.commit()

	if v.username == "Aevann": return render_template("admin/awards.html", awards=list(AWARDS.values()), v=v)
	return render_template("admin/awards.html", awards=list(AWARDS2.values()), v=v)