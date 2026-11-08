import calendar
from datetime import datetime, timezone

import matplotlib.pyplot as plt
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from files.classes.mod_logs import ACTIONTYPES, ACTIONTYPES2, ADMIN_ONLY_KINDS
from files.classes.visstate import StateMod
from files.helpers.alerts import *
from files.helpers.captcha import validate_captcha
from files.helpers.config.const import *
from files.helpers.config.environment import HCAPTCHA_SECRET, HCAPTCHA_SITEKEY, IMAGES_DIR
from files.helpers.listing import request_page
from files.helpers.media import new_image_path, process_image
from files.mail import *
from files.__main__ import app, cache, limiter # violates isort but used to prevent getting shadowed


@app.get('/sidebar')
@auth_desired
def sidebar(v):
	return render_template('sidebar.html', v=v)

@app.get('/rules')
@auth_desired
def rules(v):
	return render_template('rules.html', v=v)

@app.get('/support')
@auth_desired
def support(v):
	return render_template('support.html', v=v)

@app.get("/stats")
@admin_level_required(2)
@cache.memoize(timeout=86400, make_name=make_name)
def participation_stats(v):
	day = int(time.time()) - 86400

	week = int(time.time()) - 604800 # TODO themotte#601 use created_datetimez once all is converted
	week_datetime = datetime.fromtimestamp(week, tz=timezone.utc)
	posters = g.db.query(Submission.author_id).distinct(Submission.author_id).filter(Submission.created_utc > week).all()
	commenters = g.db.query(Comment.author_id).distinct(Comment.author_id).filter(Comment.created_utc > week).all()
	voters = g.db.query(Vote.user_id).distinct(Vote.user_id).filter(Vote.created_datetimez > week_datetime).all()
	commentvoters = g.db.query(CommentVote.user_id).distinct(CommentVote.user_id).filter(CommentVote.created_datetimez > week_datetime).all()

	active_users = set(posters) | set(commenters) | set(voters) | set(commentvoters)

	users: Query = g.db.query(User.id)
	submissions: Query = g.db.query(Submission.id)
	comments: Query = g.db.query(Comment.id)

	stats = {
		"users": users.count(),
		"private users": users.filter_by(is_private=True).count(),
		"banned users": users.filter(User.is_banned > 0).count(),
		"verified email users": users.filter_by(is_activated=True).count(),
		"signups last 24h": users.filter(User.created_utc > day).count(),
		"total posts": submissions.count(),
		"posting users": g.db.query(Submission.author_id).distinct().count(),
		"listed posts": submissions.filter(Submission.state_mod == StateMod.VISIBLE).filter(Submission.state_user_deleted_utc == None).count(),
		"removed posts (by admins)": submissions.filter(Submission.state_mod != StateMod.VISIBLE).count(),
		"deleted posts (by author)": submissions.filter(Submission.state_user_deleted_utc != None).count(),
		"posts last 24h": submissions.filter(Submission.created_utc > day).count(),
		"total comments": comments.filter(Comment.author_id.notin_((AUTOJANNY_ID,NOTIFICATIONS_ID))).count(),
		"commenting users": g.db.query(Comment.author_id).distinct().count(),
		"removed comments (by admins)": comments.filter(Comment.state_mod != StateMod.VISIBLE).count(),
		"deleted comments (by author)": comments.filter(Comment.state_user_deleted_utc != None).count(),
		"comments last_24h": comments.filter(Comment.created_utc > day, Comment.author_id.notin_((AUTOJANNY_ID,NOTIFICATIONS_ID))).count(),
		"post votes": g.db.query(Vote.submission_id).count(),
		"post voting users": g.db.query(Vote.user_id).distinct().count(),
		"comment votes": g.db.query(CommentVote.comment_id).count(),
		"comment voting users": g.db.query(CommentVote.user_id).distinct().count(),
		"total upvotes": g.db.query(Vote.submission_id).filter_by(vote_type=1).count() + g.db.query(CommentVote.comment_id).filter_by(vote_type=1).count(),
		"total downvotes": g.db.query(Vote.submission_id).filter_by(vote_type=-1).count() + g.db.query(CommentVote.comment_id).filter_by(vote_type=-1).count(),
		"users who posted, commented, or voted in the past 7 days": len(active_users),
	}
	return render_template("admin/content_stats.html", v=v, title="Content Statistics", data=stats)


@app.get("/chart")
def chart():
	return redirect('/weekly_chart')


@app.get("/weekly_chart")
@admin_level_required(2)
def weekly_chart(v):
	file = cached_chart(kind="weekly", site=SITE)
	f = send_file(file)
	return f


@app.get("/daily_chart")
@admin_level_required(2)
def daily_chart(v):
	file = cached_chart(kind="daily", site=SITE)
	f = send_file(file)
	return f


@cache.memoize(timeout=86400)
def cached_chart(kind, site):
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

	if kind == "daily": day_cutoffs = [today_cutoff - 86400 * i for i in range(47)][1:]
	else: day_cutoffs = [today_cutoff - 86400 * 7 * i for i in range(47)][1:]

	day_cutoffs.insert(0, calendar.timegm(now))

	daily_times = [time.strftime("%d/%m", time.gmtime(day_cutoffs[i + 1])) for i in range(len(day_cutoffs) - 1)][::-1]

	daily_signups = [g.db.query(User.id).filter(User.created_utc < day_cutoffs[i], User.created_utc > day_cutoffs[i + 1]).count() for i in range(len(day_cutoffs) - 1)][::-1]

	post_stats = [g.db.query(Submission.id).filter(Submission.created_utc < day_cutoffs[i], Submission.created_utc > day_cutoffs[i + 1], Submission.state_mod == StateMod.VISIBLE).count() for i in range(len(day_cutoffs) - 1)][::-1]

	comment_stats = [g.db.query(Comment.id).filter(Comment.created_utc < day_cutoffs[i], Comment.created_utc > day_cutoffs[i + 1],Comment.state_mod == StateMod.VISIBLE, Comment.author_id.notin_((AUTOJANNY_ID,NOTIFICATIONS_ID))).count() for i in range(len(day_cutoffs) - 1)][::-1]

	plt.rcParams["figure.figsize"] = (30, 20)

	signup_chart = plt.subplot2grid((30, 20), (0, 0), rowspan=6, colspan=30)
	posts_chart = plt.subplot2grid((30, 20), (10, 0), rowspan=6, colspan=30)
	comments_chart = plt.subplot2grid((30, 20), (20, 0), rowspan=6, colspan=30)

	_ = signup_chart.grid(), posts_chart.grid(), comments_chart.grid()

	signup_chart.plot(
		daily_times,
		daily_signups,
		color='red',
		label='Signups')
	posts_chart.plot(
		daily_times,
		post_stats,
		color='blue',
		label='Posts')
	comments_chart.plot(
		daily_times,
		comment_stats,
		color='purple',
		label='Comments')

	signup_chart.set_ylim(ymin=0)
	posts_chart.set_ylim(ymin=0)
	comments_chart.set_ylim(ymin=0)

	signup_chart.set_ylabel("Signups")
	posts_chart.set_ylabel("Posts")
	comments_chart.set_ylabel("Comments")
	comments_chart.set_xlabel("Time (UTC)")

	signup_chart.legend(loc='upper left', frameon=True)
	posts_chart.legend(loc='upper left', frameon=True)
	comments_chart.legend(loc='upper left', frameon=True)

	file = f"/{SITE}_{kind}.png"

	plt.savefig(file)
	plt.clf()
	return file


# What rendering an entry reads
_MOD_ACTION_LOADS = (
	selectinload(ModAction.user),
	selectinload(ModAction.target_user),
	selectinload(ModAction.target_post).selectinload(Submission.author),
	selectinload(ModAction.target_comment).selectinload(Comment.author),
	selectinload(ModAction.target_comment).selectinload(Comment.post),
)


def _sees_admin_only_kinds(v) -> bool:
	return bool(v and v.admin_level >= 2)


@app.get("/admins")
@auth_desired
def admins(v):
	if v and v.admin_level >= 3:
		admins = g.db.query(User).filter(User.admin_level>1).order_by(User.truescore.desc()).all()
		admins += g.db.query(User).filter(User.admin_level==1).order_by(User.truescore.desc()).all()
	else: admins = g.db.query(User).filter(User.admin_level>0).order_by(User.truescore.desc()).all()
	# What each admin's entries in the mod log come to for this viewer
	entries = g.db.query(ModAction.user_id, func.count()).filter(ModAction.user_id.in_([u.id for u in admins])).group_by(ModAction.user_id)
	if not _sees_admin_only_kinds(v): entries = entries.filter(ModAction.kind.notin_(ADMIN_ONLY_KINDS))
	return render_template("admins.html", v=v, admins=admins, mod_actions=dict(entries.all()))


@app.get("/log")
@app.get("/modlog")
@auth_desired
def log(v):
	page = request_page()

	admin = request.values.get("admin")
	if admin: admin_id = get_id(admin)
	else: admin_id = 0

	kind = request.values.get("kind")

	types = ACTIONTYPES if _sees_admin_only_kinds(v) else ACTIONTYPES2

	if kind not in types: kind = None

	actions = g.db.query(ModAction)
	if not _sees_admin_only_kinds(v):
		actions = actions.filter(ModAction.kind.notin_(ADMIN_ONLY_KINDS))
	
	if admin_id:
		actions = actions.filter_by(user_id=admin_id)
		kinds = set([x.kind for x in actions])
		kinds.add(kind)
		types2 = {}
		for k,val in types.items():
			if k in kinds: types2[k] = val
		types = types2
	if kind: actions = actions.filter_by(kind=kind)

	actions = actions.options(
		*_MOD_ACTION_LOADS
	).order_by(ModAction.id.desc()).offset(25*(page-1)).limit(26).all()
	next_exists=len(actions)>25
	actions=actions[:25]

	admins = [x[0] for x in g.db.query(User.username).filter(User.admin_level > 1).order_by(User.username).all()]

	return render_template("log.html", v=v, admins=admins, types=types, admin=admin, type=kind, actions=actions, next_exists=next_exists, page=page)

@app.get("/log/<id:id>")
@auth_desired
def log_item(v, id):
	action=g.db.query(ModAction).options(
		*_MOD_ACTION_LOADS
	).filter_by(id=id).one_or_none()

	if not action: abort(404)
	if action.kind in ADMIN_ONLY_KINDS and not _sees_admin_only_kinds(v): abort(404)

	admins = [x[0] for x in g.db.query(User.username).filter(User.admin_level > 1).all()]

	types = ACTIONTYPES if _sees_admin_only_kinds(v) else ACTIONTYPES2

	return render_template("log.html", v=v, actions=[action], next_exists=False, page=1, action=action, admins=admins, types=types)


@app.get("/api")
@auth_desired
def api(v):
	return render_template("api.html", v=v)

@app.get("/contact")
@app.get("/press")
@app.get("/media")
@auth_desired
def contact(v):
	return render_template("contact.html", v=v, hcaptcha=HCAPTCHA_SITEKEY)

@app.post("/send_admin")
@limiter.limit("1/second;2/minute;6/hour;10/day")
@auth_desired
def submit_contact(v: Optional[User]):
	if not v and not validate_captcha(HCAPTCHA_SECRET, HCAPTCHA_SITEKEY,
	                                  request.values.get("h-captcha-response", "")):
		abort(403, "CAPTCHA provided was not correct. Please try it again")
	body = request.values.get("message", "").strip()[:MESSAGE_BODY_LENGTH_MAXIMUM].strip()
	# The longest an email address can be
	email = request.values.get("email", "").strip()[:254]
	if not body: abort(400, "Message is empty!")

	header = "This message has been sent automatically to all admins via [/contact](/contact)\n"
	if not email:
		email = ""
	else:
		email = f"<strong>Email</strong>: {email}\n"
	message = f"<strong>Message</strong>:\n{body}\n\n"
	html    = sanitize(f"{header}\n{email}{message}")

	if request.files.get("file") and request.headers.get("cf-ipcountry") != "T1":
		file=request.files["file"]
		if (file.content_type or '').startswith('image/'):
			name = new_image_path()
			file.save(name)
			url = process_image(name)
			html += f'<img data-bs-target="#expandImageModal" data-bs-toggle="modal" onclick="expandDesktopImage(this.src)" class="img" src="{url}" loading="lazy">'
		else: abort(400, "Image files only")

	new_comment = Comment(
		author_id=v.id if v else NOTIFICATIONS_ID,
		parent_submission=None,
		level=1,
		body_html=html,
		sentto=MODMAIL_ID,
		state_mod=StateMod.VISIBLE,
	)
	g.db.add(new_comment)
	g.db.flush()
	new_comment.top_comment_id = new_comment.id
	
	notify_modmail(new_comment.id, v)



	g.db.commit()
	return render_template("contact.html", v=v, msg="Your message has been sent.")


@app.get('/assets/<path:path>')
@app.get('/static/assets/<path:path>')
@limiter.exempt
def static_service(path):
	resp = make_response(send_from_directory('assets', path))
	if request.path.endswith('.webp') or request.path.endswith('.gif') or request.path.endswith('.ttf') or request.path.endswith('.woff2'):
		resp.headers.remove("Cache-Control")
		resp.headers.add("Cache-Control", "public, max-age=3153600")
	
	# Cache CSS and JS files with version parameter
	if (request.path.endswith('.css') or request.path.endswith('.js')) and request.args.get('v'):
		resp.headers.remove("Cache-Control")
		resp.headers.add("Cache-Control", "public, max-age=3153600")

	if request.path.endswith('.webp'):
		resp.headers.remove("Content-Type")
		resp.headers.add("Content-Type", "image/webp")

	return resp

@app.get('/images/<path>')
@app.get('/hostedimages/<path>')
@app.get("/static/images/<path>")
@limiter.exempt
def images(path):
	resp = make_response(send_from_directory(IMAGES_DIR, path.replace('.WEBP','.webp')))
	resp.headers.remove("Cache-Control")
	resp.headers.add("Cache-Control", "public, max-age=3153600")
	if request.path.endswith('.webp'):
		resp.headers.remove("Content-Type")
		resp.headers.add("Content-Type", "image/webp")
	return resp

@app.get("/robots.txt")
def robots_txt():
	try: f = send_file("assets/robots.txt")
	except:
		print('/robots.txt', flush=True)
		abort(404)
	return f

@app.get("/blocks")
@admin_level_required(2)
def blocks(v):
	blocks=g.db.query(UserBlock).all()
	users = []
	targets = []
	for x in blocks:
		users.append(get_account(x.user_id))
		targets.append(get_account(x.target_id))

	return render_template("blocks.html", v=v, users=users, targets=targets)

@app.get("/banned")
@auth_desired
def banned(v):
	users = [x for x in g.db.query(User).filter(User.is_banned > 0, User.unban_utc == 0).all()]
	return render_template("banned.html", v=v, users=users)

@app.get("/formatting")
@auth_desired
def formatting(v):
	return render_template("formatting.html", v=v)

@app.get("/settings/security")
@auth_required
def settings_security(v):
	return render_template("settings_security.html",
						   v=v,
						   mfa_secret=pyotp.random_base32() if not v.mfa_secret else None
						   )

@app.post("/dismiss_mobile_tip")
def dismiss_mobile_tip():
	session["tooltip_last_dismissed"] = int(time.time())
	return "", 204
