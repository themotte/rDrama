import io
from datetime import datetime, timezone

from matplotlib.figure import Figure
from sqlalchemy import distinct, func, select, union
from sqlalchemy.orm import selectinload

from files.classes.mod_logs import ACTIONTYPES, ACTIONTYPES2, ADMIN_ONLY_KINDS
from files.classes.visstate import StateMod
from files.helpers.alerts import *
from files.helpers.assetcache import ASSET_CSS, assetcache_hash
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
def participation_stats(v):
	day = int(time.time()) - 86400

	week = int(time.time()) - 604800 # TODO themotte#601 use created_datetimez once all is converted
	week_datetime = datetime.fromtimestamp(week, tz=timezone.utc)
	count = func.count
	not_system = Comment.author_id.notin_((AUTOJANNY_ID, NOTIFICATIONS_ID))

	# One pass over each table
	users, private, banned, verified, signups = g.db.query(count(), count().filter(User.is_private == True), count().filter(User.is_banned > 0), count().filter(User.is_activated == True), count().filter(User.created_utc > day)).one()
	posts, posters, listed, removed_posts, deleted_posts, recent_posts = g.db.query(count(), count(distinct(Submission.author_id)), count().filter(Submission.state_mod == StateMod.VISIBLE, Submission.state_user_deleted_utc == None), count().filter(Submission.state_mod != StateMod.VISIBLE), count().filter(Submission.state_user_deleted_utc != None), count().filter(Submission.created_utc > day)).one()
	comments, commenters, removed_comments, deleted_comments, recent_comments = g.db.query(count().filter(not_system), count(distinct(Comment.author_id)), count().filter(Comment.state_mod != StateMod.VISIBLE), count().filter(Comment.state_user_deleted_utc != None), count().filter(Comment.created_utc > day, not_system)).one()
	post_votes, post_voters, post_up, post_down = g.db.query(count(), count(distinct(Vote.user_id)), count().filter(Vote.vote_type == 1), count().filter(Vote.vote_type == -1)).one()
	comment_votes, comment_voters, comment_up, comment_down = g.db.query(count(), count(distinct(CommentVote.user_id)), count().filter(CommentVote.vote_type == 1), count().filter(CommentVote.vote_type == -1)).one()
	active = union(
		select(Submission.author_id).where(Submission.created_utc > week),
		select(Comment.author_id).where(Comment.created_utc > week),
		select(Vote.user_id).where(Vote.created_datetimez > week_datetime),
		select(CommentVote.user_id).where(CommentVote.created_datetimez > week_datetime),
	).subquery()
	active_users = g.db.query(count()).select_from(active).scalar()

	# (id in the page, label, figure)
	stats = [
		("users", "users", users),
		("private_users", "private users", private),
		("banned_users", "banned users", banned),
		("verified_email_users", "verified email users", verified),
		("signups_24h", "signups last 24h", signups),
		("posts", "total posts", posts),
		("posting_users", "posting users", posters),
		("listed_posts", "listed posts", listed),
		("removed_posts", "removed posts (by admins)", removed_posts),
		("deleted_posts", "deleted posts (by author)", deleted_posts),
		("posts_24h", "posts last 24h", recent_posts),
		("comments", "total comments", comments),
		("commenting_users", "commenting users", commenters),
		("removed_comments", "removed comments (by admins)", removed_comments),
		("deleted_comments", "deleted comments (by author)", deleted_comments),
		("comments_24h", "comments last 24h", recent_comments),
		("post_votes", "post votes", post_votes),
		("post_voting_users", "post voting users", post_voters),
		("comment_votes", "comment votes", comment_votes),
		("comment_voting_users", "comment voting users", comment_voters),
		("upvotes", "total upvotes", post_up + comment_up),
		("downvotes", "total downvotes", post_down + comment_down),
		("active_users_7d", "users who posted, commented, or voted in the past 7 days", active_users),
	]
	return render_template("admin/content_stats.html", v=v, title="Content Statistics", data=stats)


@app.get("/chart")
def chart():
	return redirect('/weekly_chart')


@app.get("/weekly_chart")
@admin_level_required(2)
def weekly_chart(v):
	return Response(_chart_png("weekly", _utc_midnight(time.time())), mimetype="image/png")


@app.get("/daily_chart")
@admin_level_required(2)
def daily_chart(v):
	return Response(_chart_png("daily", _utc_midnight(time.time())), mimetype="image/png")


CHART_POINTS = 46


def _utc_midnight(now: float) -> int:
	return int(now) - int(now) % 86400


def _chart_series(kind: str, now: float) -> tuple[list[str], list[int], list[int], list[int]]:
	'''
	The data of the "daily" or "weekly" chart: the 46 whole UTC days (or 7-day weeks) before today's UTC midnight, oldest first, each labelled with its first day as "dd/mm", and in each, how many accounts signed up, and how many of the posts and of the comments created in it are visible (comments by the system accounts left out). Today so far isn't counted.
	'''
	span = 86400 * (7 if kind == "weekly" else 1)
	midnight = _utc_midnight(now)
	starts = [midnight - span * i for i in range(CHART_POINTS, 0, -1)]

	def counts(query, created_utc):
		point = (created_utc - starts[0]) // span
		found = dict(query.filter(created_utc >= starts[0], created_utc < midnight).with_entities(point, func.count()).group_by(point).all())
		return [found.get(i, 0) for i in range(CHART_POINTS)]

	labels = [time.strftime("%d/%m", time.gmtime(start)) for start in starts]
	signups = counts(g.db.query(User.id), User.created_utc)
	posts = counts(g.db.query(Submission.id).filter(Submission.state_mod == StateMod.VISIBLE), Submission.created_utc)
	comments = counts(g.db.query(Comment.id).filter(Comment.state_mod == StateMod.VISIBLE, Comment.author_id.notin_((AUTOJANNY_ID, NOTIFICATIONS_ID))), Comment.created_utc)
	return labels, signups, posts, comments


# By the day it's drawn on, so a new day's chart is drawn afresh
@cache.memoize(timeout=86400)
def _chart_png(kind: str, midnight: int) -> bytes:
	labels, signups, posts, comments = _chart_series(kind, midnight)

	# A figure of its own rather than pyplot's shared one: requests render concurrently
	figure = Figure(figsize=(30, 20))
	grid = figure.add_gridspec(30, 20)
	for row, (label, color, counts) in enumerate([("Signups", "red", signups), ("Posts", "blue", posts), ("Comments", "purple", comments)]):
		chart = figure.add_subplot(grid[row * 10:row * 10 + 6, :])
		chart.grid()
		chart.plot(labels, counts, color=color, label=label)
		chart.set_ylim(bottom=0)
		chart.set_ylabel(label)
		chart.legend(loc='upper left', frameon=True)
	chart.set_xlabel("Time (UTC)")

	png = io.BytesIO()
	figure.savefig(png, format="png")
	return png.getvalue()


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
	admins = g.db.query(User).filter(User.admin_level > 0).order_by((User.admin_level > 1).desc(), User.truescore.desc()).all()
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
		# The menu offers the kinds this admin's entries have
		kinds = {k for (k,) in actions.with_entities(ModAction.kind).distinct()} | {kind}
		types = {k: val for k, val in types.items() if k in kinds}
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


# For an address that only ever means one version of its file
IMMUTABLE_MAX_AGE = 365 * 86400


@app.get('/assets/<path:path>')
@app.get('/static/assets/<path:path>')
@limiter.exempt
def static_service(path):
	# Pages link site files with their current version as "v"; any other "v" may name some other version
	version = assetcache_hash(path)
	max_age = IMMUTABLE_MAX_AGE if version and request.args.get('v') == version else None
	if path in ASSET_CSS:
		return send_file(io.BytesIO(ASSET_CSS[path]), mimetype="text/css", etag=version, max_age=max_age)
	return send_from_directory('assets', path, max_age=max_age)

@app.get('/images/<path>')
@app.get('/hostedimages/<path>')
@app.get("/static/images/<path>")
@limiter.exempt
def images(path):
	# Uploads are stored under fresh names and never replaced
	return send_from_directory(IMAGES_DIR, path.replace('.WEBP','.webp'), max_age=IMMUTABLE_MAX_AGE)

@app.get("/robots.txt")
def robots_txt():
	return send_file("assets/robots.txt")

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
