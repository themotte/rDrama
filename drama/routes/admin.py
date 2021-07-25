from urllib.parse import urlparse
import time
import calendar
from sqlalchemy import func
from sqlalchemy.orm import lazyload
import threading
import subprocess
import imagehash
from os import remove
from PIL import Image as IMAGE

from drama.helpers.wrappers import *
from drama.helpers.alerts import *
from drama.helpers.base36 import *
from drama.helpers.sanitize import *
from drama.helpers.markdown import *
from drama.helpers.security import *
from drama.helpers.get import *
from drama.helpers.aws import *
from drama.classes import *
from drama.classes.domains import reasons as REASONS
from flask import *
import matplotlib.pyplot as plt
from .front import frontlist
from drama.__main__ import app, cache


@app.route("/admin/shadowbanned", methods=["GET"])
@auth_required
def shadowbanned(v):
	if v and v.is_banned and not v.unban_utc: return render_template("seized.html")
	if not (v and v.admin_level == 6): abort(404)
	users = [x for x in g.db.query(User).filter(User.shadowbanned == True).all()]
	return render_template("banned.html", v=v, users=users)


@app.route("/admin/agendaposters", methods=["GET"])
@auth_required
def agendaposters(v):
	if v and v.is_banned and not v.unban_utc: return render_template("seized.html")
	if not (v and v.admin_level == 6): abort(404)
	users = [x for x in g.db.query(User).filter(User.agendaposter == True).all()]
	return render_template("banned.html", v=v, users=users)


@app.route("/admin/flagged/posts", methods=["GET"])
@admin_level_required(3)
def flagged_posts(v):

	page = max(1, int(request.args.get("page", 1)))

	posts = g.db.query(Submission).filter_by(
		is_approved=0,
		purged_utc=0,
		is_banned=False
	).join(Submission.flags
		   ).options(contains_eager(Submission.flags)
					 ).order_by(Submission.id.desc()).offset(25 * (page - 1)).limit(26)

	listing = [p.id for p in posts]
	next_exists = (len(listing) == 26)
	listing = listing[0:25]

	listing = get_posts(listing, v=v)

	return render_template("admin/flagged_posts.html",
						   next_exists=next_exists, listing=listing, page=page, v=v)


@app.route("/admin/image_posts", methods=["GET"])
@admin_level_required(3)
@api("read")
def image_posts_listing(v):

	page = int(request.args.get('page', 1))

	posts = g.db.query(Submission).filter_by(domain_ref=1).order_by(Submission.id.desc()
																	).offset(25 * (page - 1)
																			 ).limit(26)

	posts = [x.id for x in posts]
	next_exists = (len(posts) == 26)
	posts = posts[0:25]

	posts = get_posts(posts, v=v)

	return {'html': lambda: render_template("admin/image_posts.html",
											v=v,
											listing=posts,
											next_exists=next_exists,
											page=page,
											sort="new"
											),
			'api': lambda: [x.json for x in posts]
			}


@app.route("/admin/flagged/comments", methods=["GET"])
@admin_level_required(3)
def flagged_comments(v):

	page = max(1, int(request.args.get("page", 1)))

	posts = g.db.query(Comment
					   ).filter_by(
		is_approved=0,
		purged_utc=0,
		is_banned=False
	).join(Comment.flags).options(contains_eager(Comment.flags)
								  ).order_by(Comment.id.desc()).offset(25 * (page - 1)).limit(26).all()

	listing = [p.id for p in posts]
	next_exists = (len(listing) == 26)
	listing = listing[0:25]

	listing = get_comments(listing, v=v)

	return render_template("admin/flagged_comments.html",
						   next_exists=next_exists,
						   listing=listing,
						   page=page,
						   v=v,
						   standalone=True)


@app.route("/admin", methods=["GET"])
@admin_level_required(3)
def admin_home(v):
	b = g.db.query(Board).filter_by(id=1).first()
	return render_template("admin/admin_home.html", v=v, b=b)


@app.route("/admin/badge_grant", methods=["GET"])
@admin_level_required(4)
def badge_grant_get(v):

	badge_types = g.db.query(BadgeDef).filter_by(kind=3).order_by(BadgeDef.rank).all()

	errors = {"already_owned": "That user already has that badge.",
			  "no_user": "That user doesn't exist."
			  }

	return render_template("admin/badge_grant.html",
						   v=v,
						   badge_types=badge_types,
						   error=errors.get(
							   request.args.get("error"),
							   None) if request.args.get('error') else None,
						   msg="Badge successfully assigned" if request.args.get(
							   "msg") else None
						   )


@app.route("/admin/badge_grant", methods=["POST"])
@admin_level_required(4)
@validate_formkey
def badge_grant_post(v):

	user = get_user(request.form.get("username"), graceful=True)
	if not user: return redirect("/badge_grant?error=no_user")

	badge_id = int(request.form.get("badge_id"))

	badge = g.db.query(BadgeDef).filter_by(id=badge_id).first()
	if badge.kind != 3:
		abort(403)

	if user.has_badge(badge_id):
		g.db.query(Badge).filter_by(badge_id=badge_id, user_id=user.id,).delete()
		g.db.commit()
		return redirect(user.permalink)
	
	new_badge = Badge(badge_id=badge_id,
					  user_id=user.id,
					  created_utc=int(time.time())
					  )

	desc = request.form.get("description")
	if desc: new_badge.description = desc

	url = request.form.get("url")
	if url: new_badge.url = url

	g.db.add(new_badge)

	g.db.commit()

	text = f"""
	@{v.username} has given you the following profile badge:
	\n\n![]({new_badge.path})
	\n\n{new_badge.name}
	"""

	send_notification(1046, user, text)

	if badge_id in [21,22,23,24,28]:
		user.patron = True
		user.animatedname = True
		if badge_id == 23: user.banawards = 1
		elif badge_id in [24,28]: user.banawards = 3
		g.db.add(user)
	
	return redirect(user.permalink)


@app.route("/admin/users", methods=["GET"])
@admin_level_required(2)
def users_list(v):

	page = int(request.args.get("page", 1))

	users = g.db.query(User).filter_by(is_banned=0
									   ).order_by(User.created_utc.desc()
												  ).offset(25 * (page - 1)).limit(26)

	users = [x for x in users]

	next_exists = (len(users) == 26)
	users = users[0:25]

	return render_template("admin/new_users.html",
						   v=v,
						   users=users,
						   next_exists=next_exists,
						   page=page,
						   )


@app.route("/admin/content_stats", methods=["GET"])
@admin_level_required(2)
def participation_stats(v):

	now = int(time.time())

	day = now - 86400

	data = {"valid_users": g.db.query(User).count(),
			"private_users": g.db.query(User).filter_by(is_private=False).count(),
			"banned_users": g.db.query(User).filter(User.is_banned > 0, User.unban_utc == 0).count(),
			"verified_users": g.db.query(User).filter_by(is_activated=True).count(),
			"signups_last_24h": g.db.query(User).filter(User.created_utc > day).count(),
			"total_posts": g.db.query(Submission).count(),
			"posting_users": g.db.query(Submission.author_id).distinct().count(),
			"listed_posts": g.db.query(Submission).filter_by(is_banned=False).filter(Submission.deleted_utc > 0).count(),
			"removed_posts": g.db.query(Submission).filter_by(is_banned=True).count(),
			"deleted_posts": g.db.query(Submission).filter(Submission.deleted_utc > 0).count(),
			"posts_last_24h": g.db.query(Submission).filter(Submission.created_utc > day).count(),
			"total_comments": g.db.query(Comment).count(),
			"commenting_users": g.db.query(Comment.author_id).distinct().count(),
			"removed_comments": g.db.query(Comment).filter_by(is_banned=True).count(),
			"deleted_comments": g.db.query(Comment).filter(Comment.deleted_utc>0).count(),
			"comments_last_24h": g.db.query(Comment).filter(Comment.created_utc > day).count(),
			"post_votes": g.db.query(Vote).count(),
			"post_voting_users": g.db.query(Vote.user_id).distinct().count(),
			"post_votes_last_24h": g.db.query(Vote).filter(Vote.created_utc > day).count(),
			"comment_votes": g.db.query(CommentVote).count(),
			"comment_voting_users": g.db.query(CommentVote.user_id).distinct().count(),
			"comment_votes_last_24h": g.db.query(CommentVote).filter(CommentVote.created_utc > day).count()
			}


	return render_template("admin/content_stats.html", v=v, title="Content Statistics", data=data)

@app.route("/admin/alt_votes", methods=["GET"])
@admin_level_required(4)
def alt_votes_get(v):

	if not request.args.get("u1") or not request.args.get("u2"):
		return render_template("admin/alt_votes.html", v=v)

	u1 = request.args.get("u1")
	u2 = request.args.get("u2")

	if not u1 or not u2:
		return redirect("/admin/alt_votes")

	u1 = get_user(u1)
	u2 = get_user(u2)

	u1_post_ups = g.db.query(
		Vote.submission_id).filter_by(
		user_id=u1.id,
		vote_type=1).all()
	u1_post_downs = g.db.query(
		Vote.submission_id).filter_by(
		user_id=u1.id,
		vote_type=-1).all()
	u1_comment_ups = g.db.query(
		CommentVote.comment_id).filter_by(
		user_id=u1.id,
		vote_type=1).all()
	u1_comment_downs = g.db.query(
		CommentVote.comment_id).filter_by(
		user_id=u1.id,
		vote_type=-1).all()
	u2_post_ups = g.db.query(
		Vote.submission_id).filter_by(
		user_id=u2.id,
		vote_type=1).all()
	u2_post_downs = g.db.query(
		Vote.submission_id).filter_by(
		user_id=u2.id,
		vote_type=-1).all()
	u2_comment_ups = g.db.query(
		CommentVote.comment_id).filter_by(
		user_id=u2.id,
		vote_type=1).all()
	u2_comment_downs = g.db.query(
		CommentVote.comment_id).filter_by(
		user_id=u2.id,
		vote_type=-1).all()

	data = {}
	data['u1_only_post_ups'] = len(
		[x for x in u1_post_ups if x not in u2_post_ups])
	data['u2_only_post_ups'] = len(
		[x for x in u2_post_ups if x not in u1_post_ups])
	data['both_post_ups'] = len(list(set(u1_post_ups) & set(u2_post_ups)))

	data['u1_only_post_downs'] = len(
		[x for x in u1_post_downs if x not in u2_post_downs])
	data['u2_only_post_downs'] = len(
		[x for x in u2_post_downs if x not in u1_post_downs])
	data['both_post_downs'] = len(
		list(set(u1_post_downs) & set(u2_post_downs)))

	data['u1_only_comment_ups'] = len(
		[x for x in u1_comment_ups if x not in u2_comment_ups])
	data['u2_only_comment_ups'] = len(
		[x for x in u2_comment_ups if x not in u1_comment_ups])
	data['both_comment_ups'] = len(
		list(set(u1_comment_ups) & set(u2_comment_ups)))

	data['u1_only_comment_downs'] = len(
		[x for x in u1_comment_downs if x not in u2_comment_downs])
	data['u2_only_comment_downs'] = len(
		[x for x in u2_comment_downs if x not in u1_comment_downs])
	data['both_comment_downs'] = len(
		list(set(u1_comment_downs) & set(u2_comment_downs)))

	data['u1_post_ups_unique'] = 100 * \
		data['u1_only_post_ups'] // len(u1_post_ups) if u1_post_ups else 0
	data['u2_post_ups_unique'] = 100 * \
		data['u2_only_post_ups'] // len(u2_post_ups) if u2_post_ups else 0
	data['u1_post_downs_unique'] = 100 * \
		data['u1_only_post_downs'] // len(
			u1_post_downs) if u1_post_downs else 0
	data['u2_post_downs_unique'] = 100 * \
		data['u2_only_post_downs'] // len(
			u2_post_downs) if u2_post_downs else 0

	data['u1_comment_ups_unique'] = 100 * \
		data['u1_only_comment_ups'] // len(
			u1_comment_ups) if u1_comment_ups else 0
	data['u2_comment_ups_unique'] = 100 * \
		data['u2_only_comment_ups'] // len(
			u2_comment_ups) if u2_comment_ups else 0
	data['u1_comment_downs_unique'] = 100 * \
		data['u1_only_comment_downs'] // len(
			u1_comment_downs) if u1_comment_downs else 0
	data['u2_comment_downs_unique'] = 100 * \
		data['u2_only_comment_downs'] // len(
			u2_comment_downs) if u2_comment_downs else 0

	return render_template("admin/alt_votes.html",
						   u1=u1,
						   u2=u2,
						   v=v,
						   data=data
						   )


@app.route("/admin/link_accounts", methods=["POST"])
@admin_level_required(4)
@validate_formkey
def admin_link_accounts(v):

	u1 = int(request.form.get("u1"))
	u2 = int(request.form.get("u2"))

	new_alt = Alt(
		user1=u1, 
		user2=u2,
		is_manual=True
		)

	g.db.add(new_alt)
	g.db.commit()

	return redirect(f"/admin/alt_votes?u1={g.db.query(User).get(u1).username}&u2={g.db.query(User).get(u2).username}")


@app.route("/admin/removed", methods=["GET"])
@admin_level_required(3)
def admin_removed(v):

	page = int(request.args.get("page", 1))

	ids = g.db.query(Submission.id).options(lazyload('*')).filter_by(is_banned=True).order_by(
		Submission.id.desc()).offset(25 * (page - 1)).limit(26).all()

	ids=[x[0] for x in ids]

	next_exists = len(ids) == 26

	ids = ids[0:25]

	posts = get_posts(ids, v=v)

	return render_template("admin/removed_posts.html",
						   v=v,
						   listing=posts,
						   page=page,
						   next_exists=next_exists
						   )


@app.route("/admin/appdata", methods=["GET"])
@admin_level_required(4)
def admin_appdata(v):

	url=request.args.get("link")

	if url:

		thing = get_from_permalink(url, v=v)

		return render_template(
			"admin/app_data.html",
			v=v,
			thing=thing
			)

	else:
		return render_template(
			"admin/app_data.html",
			v=v)


@app.route("/admin/domain/<domain_name>", methods=["GET"])
@admin_level_required(4)
def admin_domain_domain(domain_name, v):

	d_query=domain_name.replace("_","\_")
	domain=g.db.query(Domain).filter_by(domain=d_query).first()

	if not domain:
		domain=Domain(domain=domain_name)

	return render_template(
		"admin/manage_domain.html",
		v=v,
		domain_name=domain_name,
		domain=domain,
		reasons=REASONS
		)


@app.route("/admin/image_purge", methods=["POST"])
@admin_level_required(5)
def admin_image_purge(v):
	
	url=request.form.get("url")
	aws.delete_file(url)
	return redirect("/admin/image_purge")


@app.route("/admin/image_ban", methods=["POST"])
@admin_level_required(4)
@validate_formkey
def admin_image_ban(v):

	i=request.files['file']


	#make phash
	tempname = f"admin_image_ban_{v.username}_{int(time.time())}"

	i.save(tempname)

	h=imagehash.phash(IMAGE.open(tempname))
	h=hex2bin(str(h))

	#check db for existing
	badpic = g.db.query(BadPic).filter_by(
		phash=h
		).first()

	remove(tempname)

	if badpic:
		return render_template("admin/image_ban.html", v=v, existing=badpic)

	new_bp=BadPic(
		phash=h,
		ban_reason=request.form.get("ban_reason"),
		ban_time=int(request.form.get("ban_length",0))
		)

	g.db.add(new_bp)
	g.db.commit()

	return render_template("admin/image_ban.html", v=v, success=True)


@app.route("/agendaposter/<user_id>", methods=["POST"])
@admin_level_required(6)
@validate_formkey
def agendaposter(user_id, v):
	user = g.db.query(User).filter_by(id=user_id).first()

	expiry = request.form.get("days", 0)
	if expiry:
		expiry = int(expiry)
		expiry = g.timestamp + expiry*60*60*24
	else:
		expiry = 0

	user.agendaposter = not user.agendaposter
	user.agendaposter_expires_utc = expiry
	g.db.add(user)
	for alt in user.alts:
		if alt.admin_level > 0: break
		alt.agendaposter = user.agendaposter
		alt.agendaposter_expires_utc = expiry
		g.db.add(alt)

	note = None

	if not user.agendaposter: kind = "unagendaposter"
	else:
		kind = "agendaposter"
		note = f"for {request.form.get('days')} days" if expiry else "never expires"

	ma = ModAction(
		kind=kind,
		user_id=v.id,
		target_user_id=user.id,
		board_id=1,
		note = note
	)
	g.db.add(ma)

	if 'toast' in request.args:
		return "", 204
	else:
		return redirect(user.url)

@app.route("/disablesignups", methods=["POST"])
@admin_level_required(6)
@validate_formkey
def disablesignups(v):
	board = g.db.query(Board).filter_by(id=1).first()
	board.disablesignups = not board.disablesignups
	g.db.add(board)
	return "", 204


@app.route("/shadowban/<user_id>", methods=["POST"])
@admin_level_required(6)
@validate_formkey
def shadowban(user_id, v):
	user = g.db.query(User).filter_by(id=user_id).first()
	if user.admin_level != 0: abort(403)
	user.shadowbanned = True
	g.db.add(user)
	for alt in user.alts:
		if alt.admin_level > 0: break
		alt.shadowbanned = True
		g.db.add(alt)
	ma = ModAction(
		kind="shadowban",
		user_id=v.id,
		target_user_id=user.id,
		board_id=1,
	)
	g.db.add(ma)
	cache.delete_memoized(frontlist)
	return "", 204


@app.route("/unshadowban/<user_id>", methods=["POST"])
@admin_level_required(6)
@validate_formkey
def unshadowban(user_id, v):
	user = g.db.query(User).filter_by(id=user_id).first()
	if user.admin_level != 0: abort(403)
	user.shadowbanned = False
	g.db.add(user)
	for alt in user.alts:
		alt.shadowbanned = False
		g.db.add(alt)

	ma = ModAction(
		kind="unshadowban",
		user_id=v.id,
		target_user_id=user.id,
		board_id=1,
	)
	g.db.add(ma)
	cache.delete_memoized(frontlist)
	return "", 204


@app.route("/admin/title_change/<user_id>", methods=["POST"])
@admin_level_required(6)
@validate_formkey
def admin_title_change(user_id, v):

	user = g.db.query(User).filter_by(id=user_id).first()

	if user.admin_level != 0: abort(403)

	new_name=request.form.get("title").strip()

	user.customtitleplain=new_name
	new_name=new_name.replace('_','\_')
	new_name = sanitize(new_name, linkgen=True)

	user=g.db.query(User).with_for_update().options(lazyload('*')).filter_by(id=user.id).first()
	user.customtitle=new_name
	user.flairchanged = bool(request.form.get("locked"))
	g.db.add(user)

	if user.flairchanged: kind = "set_flair_locked"
	else: kind = "set_flair_notlocked"
	
	ma=ModAction(
		kind=kind,
		user_id=v.id,
		target_user_id=user.id,
		board_id=1,
		note=f'"{new_name}"'
		)
	g.db.add(ma)

	return (redirect(user.url), user)

@app.route("/api/ban_user/<user_id>", methods=["POST"])
@admin_level_required(6)
@validate_formkey
def ban_user(user_id, v):
	
	user = g.db.query(User).filter_by(id=user_id).first()

	if user.admin_level != 0: abort(403)

	# check for number of days for suspension
	days = int(request.form.get("days")) if request.form.get('days') else 0
	reason = request.form.get("reason", "")
	message = request.form.get("reason", "")

	if not user: abort(400)

	if user.admin_level > 0: abort(403)
	
	if days > 0:
		if message:
			text = f"Your Drama account has been suspended for {days} days for the following reason:\n\n> {message}"
		else:
			text = f"Your Drama account has been suspended for {days} days."
		user.ban(admin=v, reason=reason, days=days)

	else:
		if message:
			text = f"Your Drama account has been permanently suspended for the following reason:\n\n> {message}"
		else:
			text = "Your Drama account has been permanently suspended."

		user.ban(admin=v, reason=reason)


	for x in user.alts:
		if x.admin_level > 0: break
		x.ban(admin=v, reason=reason)

	send_notification(1046, user, text)
	
	if days == 0: duration = "permenant"
	elif days == 1: duration = "1 day"
	else: duration = f"{days} days"
	ma=ModAction(
		kind="exile_user",
		user_id=v.id,
		target_user_id=user.id,
		board_id=1,
        note=f'reason: "{reason}", duration: {duration}'
		)
	g.db.add(ma)
	g.db.commit()

	if request.args.get("notoast"): return (redirect(user.url), user)

	return jsonify({"message": f"@{user.username} was banned"})


@app.route("/api/unban_user/<user_id>", methods=["POST"])
@admin_level_required(6)
@validate_formkey
def unban_user(user_id, v):

	user = g.db.query(User).filter_by(id=user_id).first()

	if not user:
		abort(400)

	user.unban()

	for x in user.alts:
		if x.admin_level == 0:
			x.unban()

	send_notification(1046, user,
					  "Your Drama account has been reinstated. Please carefully review and abide by the [rules](/post/2510) to ensure that you don't get suspended again.")

	ma=ModAction(
		kind="unexile_user",
		user_id=v.id,
		target_user_id=user.id,
		board_id=1,
		)
	g.db.add(ma)
	g.db.commit()
	
	if request.args.get("notoast"): return (redirect(user.url), user)
	return jsonify({"message": f"@{user.username} was unbanned"})

@app.route("/api/ban_post/<post_id>", methods=["POST"])
@admin_level_required(3)
@validate_formkey
def ban_post(post_id, v):

	post = g.db.query(Submission).filter_by(id=base36decode(post_id)).first()

	if not post:
		abort(400)

	post.is_banned = True
	post.is_approved = 0
	post.approved_utc = 0
	post.stickied = False
	post.is_pinned = False

	ban_reason=request.form.get("reason", "")
	ban_reason = ban_reason.replace("\n", "\n\n")
	with CustomRenderer() as renderer:
		ban_reason = renderer.render(mistletoe.Document(ban_reason))
	ban_reason = sanitize(ban_reason, linkgen=True)

	post.ban_reason = ban_reason

	g.db.add(post)

	cache.delete_memoized(frontlist)

	ma=ModAction(
		kind="ban_post",
		user_id=v.id,
		target_submission_id=post.id,
		board_id=post.board_id,
		)
	g.db.add(ma)
	return "", 204


@app.route("/api/unban_post/<post_id>", methods=["POST"])
@admin_level_required(3)
@validate_formkey
def unban_post(post_id, v):

	post = g.db.query(Submission).filter_by(id=base36decode(post_id)).first()

	if not post:
		abort(400)

	if post.is_banned:
		ma=ModAction(
			kind="unban_post",
			user_id=v.id,
			target_submission_id=post.id,
			board_id=post.board_id,
		)
		g.db.add(ma)

	post.is_banned = False
	post.is_approved = v.id
	post.approved_utc = int(time.time())

	g.db.add(post)

	cache.delete_memoized(frontlist)

	return "", 204


@app.route("/api/distinguish/<post_id>", methods=["POST"])
@admin_level_required(1)
@validate_formkey
def api_distinguish_post(post_id, v):

	post = g.db.query(Submission).filter_by(id=base36decode(post_id)).first()

	if not post:
		abort(404)

	if not post.author_id == v.id:
		abort(403)

	if post.distinguish_level:
		post.distinguish_level = 0
	else:
		post.distinguish_level = v.admin_level

	g.db.add(post)

	return "", 204


@app.route("/api/sticky/<post_id>", methods=["POST"])
@admin_level_required(3)
def api_sticky_post(post_id, v):

	post = g.db.query(Submission).filter_by(id=base36decode(post_id)).first()
	if post:
		post.stickied = not (post.stickied)
		g.db.add(post)
		g.db.commit()
		cache.delete_memoized(frontlist)

	return "", 204

@app.route("/api/pin/<post_id>", methods=["POST"])
@auth_required
def api_pin_post(post_id, v):

	post = g.db.query(Submission).filter_by(id=base36decode(post_id)).first()
	if post:
		post.is_pinned = not (post.is_pinned)
		g.db.add(post)

	return "", 204

@app.route("/api/ban_comment/<c_id>", methods=["post"])
@admin_level_required(1)
def api_ban_comment(c_id, v):

	comment = g.db.query(Comment).filter_by(id=base36decode(c_id)).first()
	if not comment:
		abort(404)

	comment.is_banned = True
	comment.is_approved = 0
	comment.approved_utc = 0

	g.db.add(comment)
	ma=ModAction(
		kind="ban_comment",
		user_id=v.id,
		target_comment_id=comment.id,
		board_id=comment.post.board_id,
		)
	g.db.add(ma)
	return "", 204


@app.route("/api/unban_comment/<c_id>", methods=["post"])
@admin_level_required(1)
def api_unban_comment(c_id, v):

	comment = g.db.query(Comment).filter_by(id=base36decode(c_id)).first()
	if not comment:
		abort(404)
	g.db.add(comment)

	if comment.is_banned:
		ma=ModAction(
			kind="unban_comment",
			user_id=v.id,
			target_comment_id=comment.id,
			board_id=comment.post.board_id,
			)
		g.db.add(ma)

	comment.is_banned = False
	comment.is_approved = v.id
	comment.approved_utc = int(time.time())


	return "", 204


@app.route("/api/distinguish_comment/<c_id>", methods=["post"])
@app.route("/api/v1/distinguish_comment/<c_id>", methods=["post"])
@auth_required
@api("read")
def admin_distinguish_comment(c_id, v):
	
	if v.admin_level == 0: abort(403)
	
	comment = get_comment(c_id, v=v)

	if comment.author_id != v.id:
		abort(403)

	comment.distinguish_level = 0 if comment.distinguish_level else v.admin_level

	g.db.add(comment)
	g.db.commit()
	html=render_template(
				"comments.html",
				v=v,
				comments=[comment],
				render_replies=False,
				is_allowed_to_comment=True
				)

	html=str(BeautifulSoup(html, features="html.parser").find(id=f"comment-{comment.base36id}-only"))

	return jsonify({"html":html, "api":html})


@app.route("/admin/dump_cache", methods=["GET"])
@admin_level_required(6)
def admin_dump_cache(v):
	cache.clear()
	return jsonify({"message": "Internal cache cleared."})


@app.route("/admin/ban_domain", methods=["POST"])
@admin_level_required(4)
@validate_formkey
def admin_ban_domain(v):

	domain=request.form.get("domain",'').strip()

	if not domain:
		abort(400)

	reason=int(request.form.get("reason",0))
	if not reason:
		abort(400)

	d_query=domain.replace("_","\_")
	d=g.db.query(Domain).filter_by(domain=d_query).first()
	if d:
		d.can_submit=False
		d.can_comment=False
		d.reason=reason
	else:
		d=Domain(
			domain=domain,
			can_submit=False,
			can_comment=False,
			reason=reason,
			show_thumbnail=False,
			embed_function=None,
			embed_template=None
			)

	g.db.add(d)
	g.db.commit()
	return redirect(d.permalink)


@app.route("/admin/nuke_user", methods=["POST"])
@admin_level_required(4)
@validate_formkey
def admin_nuke_user(v):

	user=get_user(request.form.get("user"))

	for post in g.db.query(Submission).filter_by(author_id=user.id).all():
		if post.is_banned:
			continue
			
		post.is_banned=True
		g.db.add(post)

	for comment in g.db.query(Comment).filter_by(author_id=user.id).all():
		if comment.is_banned:
			continue

		comment.is_banned=True
		g.db.add(comment)

	ma=ModAction(
		kind="nuke_user",
		user_id=v.id,
		target_user_id=user.id,
		board_id=1,
		)
	g.db.add(ma)

	return redirect(user.permalink)

@app.route("/admin/unnuke_user", methods=["POST"])
@admin_level_required(4)
@validate_formkey
def admin_nunuke_user(v):

	user=get_user(request.form.get("user"))

	for post in g.db.query(Submission).filter_by(author_id=user.id).all():
		if not post.is_banned:
			continue
			
		post.is_banned=False
		g.db.add(post)

	for comment in g.db.query(Comment).filter_by(author_id=user.id).all():
		if not comment.is_banned:
			continue

		comment.is_banned=False
		g.db.add(comment)

	ma=ModAction(
		kind="unnuke_user",
		user_id=v.id,
		target_user_id=user.id,
		board_id=1,
		)
	g.db.add(ma)

	return redirect(user.permalink)
	
@app.route("/api/user_stat_data", methods=['GET'])
@admin_level_required(2)
@cache.memoize(timeout=60)
def user_stat_data(v):

	days = int(request.args.get("days", 25))

	now = time.gmtime()
	midnight_this_morning = time.struct_time((now.tm_year,
											  now.tm_mon,
											  now.tm_mday,
											  0,
											  0,
											  0,
											  now.tm_wday,
											  now.tm_yday,
											  0)
											 )
	today_cutoff = calendar.timegm(midnight_this_morning)

	day = 3600 * 24

	day_cutoffs = [today_cutoff - day * i for i in range(days)]
	day_cutoffs.insert(0, calendar.timegm(now))

	daily_signups = [{"date": time.strftime("%d", time.gmtime(day_cutoffs[i + 1])),
					  "day_start":day_cutoffs[i + 1],
					  "signups": g.db.query(User).filter(User.created_utc < day_cutoffs[i],
														 User.created_utc > day_cutoffs[i + 1],
														 User.is_banned == 0
														 ).count()
					  } for i in range(len(day_cutoffs) - 1)
					 ]

	user_stats = {'current_users': g.db.query(User).filter_by(is_banned=0, reserved=None).count(),
				  'banned_users': g.db.query(User).filter(User.is_banned != 0).count(),
				  'reserved_users': g.db.query(User).filter(User.reserved is not None).count(),
				  'email_verified_users': g.db.query(User).filter_by(is_banned=0, is_activated=True).count(),
				  'real_id_verified_users': g.db.query(User).filter(User.reserved is not None, User.real_id is not None).count()
				  }

	post_stats = [{"date": time.strftime("%d", time.gmtime(day_cutoffs[i + 1])),
				   "day_start":day_cutoffs[i + 1],
				   "posts": g.db.query(Submission).filter(Submission.created_utc < day_cutoffs[i],
														  Submission.created_utc > day_cutoffs[i + 1],
														  Submission.is_banned == False
														  ).count()
				   } for i in range(len(day_cutoffs) - 1)
				  ]

	comment_stats = [{"date": time.strftime("%d", time.gmtime(day_cutoffs[i + 1])),
					  "day_start": day_cutoffs[i + 1],
					  "comments": g.db.query(Comment).filter(Comment.created_utc < day_cutoffs[i],
															 Comment.created_utc > day_cutoffs[i + 1],
															 Comment.is_banned == False,
															 Comment.author_id != 1
															 ).count()
					  } for i in range(len(day_cutoffs) - 1)
					 ]

	vote_stats = [{"date": time.strftime("%d", time.gmtime(day_cutoffs[i + 1])),
				   "day_start": day_cutoffs[i + 1],
				   "votes": g.db.query(Vote).join(Vote.user).filter(Vote.created_utc < day_cutoffs[i],
																	Vote.created_utc > day_cutoffs[i + 1],
																	User.is_banned == 0
																	).count()
				   } for i in range(len(day_cutoffs) - 1)
				  ]

	x = create_plot(sign_ups={'daily_signups': daily_signups},
					posts={'post_stats': post_stats},
					comments={'comment_stats': comment_stats},
					votes={'vote_stats': vote_stats}
					)

	final = {
			"multi_plot": x,
			"user_stats": user_stats,
			"signup_data": daily_signups,
			"post_data": post_stats,
			"comment_data": comment_stats,
			"vote_data": vote_stats
			}

	return jsonify(final)


def create_plot(**kwargs):

	if not kwargs:
		return abort(400)

	# create multiple charts
	daily_signups = [d["signups"] for d in kwargs["sign_ups"]['daily_signups']][::-1]
	post_stats = [d["posts"] for d in kwargs["posts"]['post_stats']][::-1]
	comment_stats = [d["comments"] for d in kwargs["comments"]['comment_stats']][::-1]
	vote_stats = [d["votes"] for d in kwargs["votes"]['vote_stats']][::-1]
	daily_times = [d["date"] for d in kwargs["sign_ups"]['daily_signups']]

	multi_plots = multiple_plots(sign_ups=daily_signups,
								 posts=post_stats,
								 comments=comment_stats,
								 votes=vote_stats,
								 daily_times=daily_times)

	return multi_plots


def multiple_plots(**kwargs):

	# create multiple charts
	signup_chart = plt.subplot2grid((20, 4), (0, 0), rowspan=5, colspan=4)
	posts_chart = plt.subplot2grid((20, 4), (5, 0), rowspan=5, colspan=4)
	comments_chart = plt.subplot2grid((20, 4), (10, 0), rowspan=5, colspan=4)
	votes_chart = plt.subplot2grid((20, 4), (15, 0), rowspan=5, colspan=4)

	signup_chart.grid(), posts_chart.grid(
	), comments_chart.grid(), votes_chart.grid()

	signup_chart.plot(
		kwargs['daily_times'][::-1],
		kwargs['sign_ups'],
		color='red')
	posts_chart.plot(
		kwargs['daily_times'][::-1],
		kwargs['posts'],
		color='green')
	comments_chart.plot(
		kwargs['daily_times'][::-1],
		kwargs['comments'],
		color='gold')
	votes_chart.plot(
		kwargs['daily_times'][::-1],
		kwargs['votes'],
		color='silver')

	signup_chart.set_ylabel("Signups")
	posts_chart.set_ylabel("Posts")
	comments_chart.set_ylabel("Comments")
	votes_chart.set_ylabel("Votes")
	comments_chart.set_xlabel("Time (UTC)")
	votes_chart.set_xlabel("Time (UTC)")

	signup_chart.legend(loc='upper left', frameon=True)
	posts_chart.legend(loc='upper left', frameon=True)
	comments_chart.legend(loc='upper left', frameon=True)
	votes_chart.legend(loc='upper left', frameon=True)

	now = int(time.time())
	name = "multiplot.png"

	plt.savefig(name)
	plt.clf()

	return upload_from_file(name, name)