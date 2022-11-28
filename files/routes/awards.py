from files.__main__ import app, limiter
from files.helpers.wrappers import *
from files.helpers.alerts import *
from files.helpers.get import *
from files.helpers.const import *
from files.classes.award import *
from .front import frontlist
from flask import g, request
from files.helpers.sanitize import filter_emojis_only
from copy import deepcopy

@app.get("/shop")
@app.get("/settings/shop")
@admin_level_required(2)
def shop(v):
	abort(404) # disable entirely pending possible future use of coins

	AWARDS = deepcopy(AWARDS2)

	for val in AWARDS.values(): val["owned"] = 0

	for useraward in g.db.query(AwardRelationship).filter(AwardRelationship.user_id == v.id, AwardRelationship.submission_id == None, AwardRelationship.comment_id == None).all():
		if useraward.kind in AWARDS: AWARDS[useraward.kind]["owned"] += 1

	for val in AWARDS.values():
		val["baseprice"] = int(val["price"])
		val["price"] = int(val["price"] * v.discount)

	sales = g.db.query(func.sum(User.coins_spent)).scalar()
	return render_template("shop.html", awards=list(AWARDS.values()), v=v, sales=sales)


@app.post("/buy/<award>")
@auth_required
def buy(v, award):
	abort(404) # disable entirely pending possible future use of coins

	if award == 'benefactor' and not request.values.get("mb"):
		abort(403, "You can only buy the Benefactor award with marseybux.")

	if award == 'ghost' and v.admin_level < 2:
		abort(403, "Only admins can buy that award.")

	AWARDS = deepcopy(AWARDS2)

	if award not in AWARDS: abort(400)
	og_price = AWARDS[award]["price"]

	price = int(og_price * v.discount)

	if request.values.get("mb"):
		if v.procoins < price: abort(400, "Not enough marseybux.")
		if award == "grass": abort(403, "You can't buy the grass award with marseybux.")
		v.procoins -= price
	else:
		if v.coins < price: abort(400, "Not enough coins.")
		v.coins -= price
		v.coins_spent += price
		if v.coins_spent >= 1000000 and not v.has_badge(73):
			new_badge = Badge(badge_id=73, user_id=v.id)
			g.db.add(new_badge)
			g.db.flush()
			send_notification(v.id, f"@AutoJanny has given you the following profile badge:\n\n![]({new_badge.path})\n\n{new_badge.name}")
		elif v.coins_spent >= 500000 and not v.has_badge(72):
			new_badge = Badge(badge_id=72, user_id=v.id)
			g.db.add(new_badge)
			g.db.flush()
			send_notification(v.id, f"@AutoJanny has given you the following profile badge:\n\n![]({new_badge.path})\n\n{new_badge.name}")
		elif v.coins_spent >= 250000 and not v.has_badge(71):
			
			new_badge = Badge(badge_id=71, user_id=v.id)
			g.db.add(new_badge)
			g.db.flush()
			send_notification(v.id, f"@AutoJanny has given you the following profile badge:\n\n![]({new_badge.path})\n\n{new_badge.name}")
		elif v.coins_spent >= 100000 and not v.has_badge(70):
			new_badge = Badge(badge_id=70, user_id=v.id)
			g.db.add(new_badge)
			g.db.flush()
			send_notification(v.id, f"@AutoJanny has given you the following profile badge:\n\n![]({new_badge.path})\n\n{new_badge.name}")
		elif v.coins_spent >= 10000 and not v.has_badge(69):
			new_badge = Badge(badge_id=69, user_id=v.id)
			g.db.add(new_badge)
			g.db.flush()
			send_notification(v.id, f"@AutoJanny has given you the following profile badge:\n\n![]({new_badge.path})\n\n{new_badge.name}")
		g.db.add(v)


	if award == "lootbox":
		send_repeatable_notification(995, f"@{v.username} bought a lootbox!")
		for i in [1,2,3,4,5]:
			award = random.choice(["snow", "gingerbread", "lights", "candycane", "fireplace"])
			award = AwardRelationship(user_id=v.id, kind=award)
			g.db.add(award)
			g.db.flush()
		v.lootboxes_bought += 1
		if v.lootboxes_bought == 10 and not v.has_badge(76):
			new_badge = Badge(badge_id=76, user_id=v.id)
			g.db.add(new_badge)
			g.db.flush()
			send_notification(v.id, f"@AutoJanny has given you the following profile badge:\n\n![]({new_badge.path})\n\n{new_badge.name}")
		elif v.lootboxes_bought == 50 and not v.has_badge(77):
			new_badge = Badge(badge_id=77, user_id=v.id)
			g.db.add(new_badge)
			g.db.flush()
			send_notification(v.id, f"@AutoJanny has given you the following profile badge:\n\n![]({new_badge.path})\n\n{new_badge.name}")
		elif v.lootboxes_bought == 150 and not v.has_badge(78):
			new_badge = Badge(badge_id=78, user_id=v.id)
			g.db.add(new_badge)
			g.db.flush()
			send_notification(v.id, f"@AutoJanny has given you the following profile badge:\n\n![]({new_badge.path})\n\n{new_badge.name}")

	else:
		award_object = AwardRelationship(user_id=v.id, kind=award)
		g.db.add(award_object)

	g.db.add(v)
	g.db.commit()

	return {"message": "Award bought!"}

@app.post("/award_post/<pid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@is_not_permabanned
def award_post(pid, v):
	abort(404) # disable entirely pending possible future use of coins

	if v.shadowbanned: return render_template('errors/500.html', err=True, v=v), 500
	
	kind = request.values.get("kind", "").strip()
	
	if kind not in AWARDS:
		abort(404, "That award doesn't exist.")

	post_award = g.db.query(AwardRelationship).filter(
		AwardRelationship.kind == kind,
		AwardRelationship.user_id == v.id,
		AwardRelationship.submission_id == None,
		AwardRelationship.comment_id == None
	).first()

	if not post_award:
		abort(404, "You don't have that award.")

	post = g.db.query(Submission).filter_by(id=pid).one_or_none()

	if not post:
		abort(404, "That post doesn't exist.")

	post_award.submission_id = post.id
	g.db.add(post_award)

	note = request.values.get("note", "").strip()

	author = post.author

	if kind == "benefactor" and author.id == v.id:
		abort(400, "You can't use this award on yourself.")

	if v.id != author.id:
		msg = f"@{v.username} has given your [post]({post.shortlink}) the {AWARDS[kind]['title']} Award!"
		if note: msg += f"\n\n> {note}"
		send_repeatable_notification(author.id, msg)

	if kind == "ban":
		link = f"[this post]({post.shortlink})"

		if not author.is_suspended:
			author.ban(reason=f"1-Day ban award used by @{v.username} on /post/{post.id}", days=1)
			send_repeatable_notification(author.id, f"Your account has been banned for **a day** for {link}. It sucked and you should feel bad.")
		elif author.unban_utc:
			author.unban_utc += 86400
			send_repeatable_notification(author.id, f"Your account has been banned for **yet another day** for {link}. Seriously man?")
	elif kind == "unban":
		if not author.is_suspended or not author.unban_utc or time.time() > author.unban_utc: abort(403)

		if author.unban_utc - time.time() > 86400:
			author.unban_utc -= 86400
			send_repeatable_notification(author.id, "Your ban duration has been reduced by 1 day!")
		else:
			author.unban_utc = 0
			author.is_banned = 0
			author.ban_evade = 0
			send_repeatable_notification(author.id, "You have been unbanned!")
	elif kind == "pin":
		if post.stickied and post.stickied_utc:
			post.stickied_utc += 3600
		else:
			post.stickied = f'{v.username} (pin award)'
			post.stickied_utc = int(time.time()) + 3600
		g.db.add(post)
		cache.delete_memoized(frontlist)
	elif kind == "unpin":
		if not post.stickied_utc: abort(403)
		t = post.stickied_utc - 3600
		if time.time() > t:
			post.stickied = None
			post.stickied_utc = None
			cache.delete_memoized(frontlist)
		else: post.stickied_utc = t
		g.db.add(post)
	elif kind == "benefactor":
		author.patron = 1
		if author.patron_utc: author.patron_utc += 2629746
		else: author.patron_utc = int(time.time()) + 2629746
		author.procoins += 2500
		if not v.has_badge(103):
			badge = Badge(user_id=v.id, badge_id=103)
			g.db.add(badge)
			g.db.flush()
			send_notification(v.id, f"@AutoJanny has given you the following profile badge:\n\n![]({badge.path})\n\n{badge.name}")

	if author.received_award_count: author.received_award_count += 1
	else: author.received_award_count = 1
	g.db.add(author)

	g.db.commit()
	if request.referrer and len(request.referrer) > 1:
		if request.referrer == f'{SITE_FULL}/submit': return redirect(post.permalink)
		elif request.referrer.startswith(f'{SITE_FULL}/'): return redirect(request.referrer)
	return redirect(SITE_FULL)


@app.post("/award_comment/<cid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@is_not_permabanned
def award_comment(cid, v):
	abort(404) # disable entirely pending possible future use of coins

	if v.shadowbanned: return render_template('errors/500.html', err=True, v=v), 500

	kind = request.values.get("kind", "").strip()

	if kind not in AWARDS:
		abort(404, "That award doesn't exist.")

	comment_award = g.db.query(AwardRelationship).filter(
		AwardRelationship.kind == kind,
		AwardRelationship.user_id == v.id,
		AwardRelationship.submission_id == None,
		AwardRelationship.comment_id == None
	).first()

	if not comment_award:
		abort(404, "You don't have that award.")

	c = g.db.query(Comment).filter_by(id=cid).one_or_none()

	if not c:
		abort(404, "That comment doesn't exist.")

	comment_award.comment_id = c.id
	g.db.add(comment_award)

	note = request.values.get("note", "").strip()

	author = c.author

	if v.id != author.id:
		msg = f"@{v.username} has given your [comment]({c.shortlink}) the {AWARDS[kind]['title']} Award!"
		if note: msg += f"\n\n> {note}"
		send_repeatable_notification(author.id, msg)

	if kind == "benefactor" and author.id == v.id:
		abort(400, "You can't use this award on yourself.")

	if kind == "ban":
		link = f"[this comment]({c.shortlink})"

		if not author.is_suspended:
			author.ban(reason=f"1-Day ban award used by @{v.username} on /comment/{c.id}", days=1)
			send_repeatable_notification(author.id, f"Your account has been banned for **a day** for {link}. It sucked and you should feel bad.")
		elif author.unban_utc:
			author.unban_utc += 86400
			send_repeatable_notification(author.id, f"Your account has been banned for **yet another day** for {link}. Seriously man?")
	elif kind == "unban":
		if not author.is_suspended or not author.unban_utc or time.time() > author.unban_utc: abort(403)

		if author.unban_utc - time.time() > 86400:
			author.unban_utc -= 86400
			send_repeatable_notification(author.id, "Your ban duration has been reduced by 1 day!")
		else:
			author.unban_utc = 0
			author.is_banned = 0
			author.ban_evade = 0
			send_repeatable_notification(author.id, "You have been unbanned!")
	elif kind == "pin":
		if c.is_pinned and c.is_pinned_utc: c.is_pinned_utc += 3600
		else:
			c.is_pinned = f'{v.username} (pin award)'
			c.is_pinned_utc = int(time.time()) + 3600
		g.db.add(c)
	elif kind == "unpin":
		if not c.is_pinned_utc: abort(403)
		t = c.is_pinned_utc - 3600
		if time.time() > t:
			c.is_pinned = None
			c.is_pinned_utc = None
		else: c.is_pinned_utc = t
		g.db.add(c)
	elif kind == "benefactor":
		author.patron = 1
		if author.patron_utc: author.patron_utc += 2629746
		else: author.patron_utc = int(time.time()) + 2629746
		author.procoins += 2500
		if not v.has_badge(103):
			badge = Badge(user_id=v.id, badge_id=103)
			g.db.add(badge)
			g.db.flush()
			send_notification(v.id, f"@AutoJanny has given you the following profile badge:\n\n![]({badge.path})\n\n{badge.name}")

	if author.received_award_count: author.received_award_count += 1
	else: author.received_award_count = 1
	g.db.add(author)

	g.db.commit()
	if request.referrer and len(request.referrer) > 1 and request.referrer.startswith(f'{SITE_FULL}/'):
		return redirect(request.referrer)
	return redirect(SITE_FULL)

@app.get("/admin/awards")
@admin_level_required(2)
def admin_userawards_get(v):
	abort(404) # disable entirely pending possible future use of coins

	if v.admin_level != 3:
		return render_template("admin/awards.html", awards=list(AWARDS3.values()), v=v)

	return render_template("admin/awards.html", awards=list(AWARDS.values()), v=v) 

@app.post("/admin/awards")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@admin_level_required(2)
def admin_userawards_post(v):
	abort(404) # disable entirely pending possible future use of coins

	try: u = request.values.get("username").strip()
	except: abort(404)

	whitelist = ("shit", "fireflies", "train", "scooter", "wholesome", "tilt", "glowie")

	u = get_user(u, graceful=False, v=v)

	notify_awards = {}

	for key, value in request.values.items():
		if key not in AWARDS: continue

		if v.admin_level < 3 and key not in whitelist: continue

		if value:
			
			if int(value) > 10: abort(403)

			if int(value): notify_awards[key] = int(value)

			for x in range(int(value)):
				award = AwardRelationship(
					user_id=u.id,
					kind=key
				)

				g.db.add(award)

	if v.id != u.id:
		text = f"@{v.username} has given the following awards:\n\n"
		for key, value in notify_awards.items():
			text += f" - **{value}** {AWARDS[key]['title']} {'Awards' if value != 1 else 'Award'}\n"
		send_repeatable_notification(u.id, text)

	note = ""

	for key, value in notify_awards.items():
		note += f"{value} {AWARDS[key]['title']}, "

	if len(note) > 256: abort(400, "You're giving too many awards at the same time!")
	
	ma=ModAction(
		kind="grant_awards",
		user_id=v.id,
		target_user_id=u.id,
		_note=note[:-2]
		)
	g.db.add(ma)

	g.db.commit()

	if v.admin_level != 3: return render_template("admin/awards.html", awards=list(AWARDS3.values()), v=v)
	return render_template("admin/awards.html", awards=list(AWARDS.values()), v=v) 
