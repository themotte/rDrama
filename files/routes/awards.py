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

	AWARDS = deepcopy(AWARDS_ENABLED)

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
def buy(v: User, award):
	abort(404) # disable entirely pending possible future use of coins

	if award == 'benefactor' and not request.values.get("mb"):
		abort(403, "You can only buy the Benefactor award with marseybux.")

	if award == 'ghost' and v.admin_level < 2:
		abort(403, "Only admins can buy that award.")

	AWARDS = deepcopy(AWARDS_ENABLED)

	if award not in AWARDS: abort(400)
	og_price = AWARDS[award]["price"]

	price = int(og_price * v.discount)

	if request.values.get("mb"):
		if v.procoins < price: abort(400, "Not enough marseybux.")
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
		return render_template("admin/awards.html", awards=list(AWARDS_JL2_PRINTABLE.values()), v=v)

	return render_template("admin/awards.html", awards=list(AWARDS.values()), v=v) 

@app.post("/admin/awards")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@admin_level_required(2)
def admin_userawards_post(v):
	abort(404) # disable entirely pending possible future use of coins

	try: u = request.values.get("username").strip()
	except: abort(404)
	whitelist = ()
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

	if v.admin_level < 3:
		awards: dict = AWARDS_JL2_PRINTABLE
	else:
		awards: dict = AWARDS

	return render_template("admin/awards.html", awards=awards, v=v) 
