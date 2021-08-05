from files.mail import *
from files.__main__ import app, limiter
from files.helpers.alerts import *

site = environ.get("DOMAIN").strip()

@app.get("/patrons")
@auth_desired
def patrons(v):
	if v and v.is_banned and not v.unban_utc: return render_template("seized.html")
	users = [x for x in g.db.query(User).filter(User.patron > 0).order_by(User.patron.desc()).all()]
	return render_template("patrons.html", v=v, users=users)

@app.get("/badmins")
@auth_desired
def badmins(v):
	badmins = g.db.query(User).filter_by(admin_level=6).order_by(User.coins.desc()).all()
	return render_template("badmins.html", v=v, badmins=badmins)

@app.get("/log")
@auth_desired
def log(v):

	page=int(request.args.get("page",1))

	if v and v.admin_level == 6: actions = g.db.query(ModAction).order_by(ModAction.id.desc()).offset(25 * (page - 1)).limit(26).all()
	else: actions=g.db.query(ModAction).filter(ModAction.kind!="shadowban", ModAction.kind!="unshadowban").order_by(ModAction.id.desc()).offset(25*(page-1)).limit(26).all()

	next_exists=len(actions)==26
	actions=actions[:25]

	return render_template("log.html", v=v, actions=actions, next_exists=next_exists, page=page)

@app.get("/log/<id>")
@auth_desired
def log_item(id, v):

	try: id = int(id)
	except:
		try: id = int(id, 36)
		except: abort(404)

	action=g.db.query(ModAction).filter_by(id=id).first()

	if not action:
		abort(404)

	if request.path != action.permalink:
		return redirect(action.permalink)

	return render_template("log.html",
		v=v,
		actions=[action],
		next_exists=False,
		page=1,
		action=action
		)

@app.route("/sex")
def index():
    return render_template("index.html", **{"greeting": "Hello from Flask!"})

@app.get("/assets/favicon.ico")
def favicon():
	return send_file("./assets/images/favicon.png")

@app.get("/api")
@auth_desired
def api(v):
	return render_template("api.html", v=v)

@app.get("/contact")
@auth_desired
def contact(v):
	if v and v.is_banned and not v.unban_utc: return render_template("seized.html")
	return render_template("contact.html", v=v)

@app.post("/contact")
@auth_desired
def submit_contact(v):
	message = f'This message has been sent automatically to all admins via https://{site}/contact, user email is "{v.email}"\n\nMessage:\n\n' + request.form.get("message", "")
	send_admin(v.id, message)
	return render_template("contact.html", v=v, msg="Your message has been sent.")

@app.route('/archives')
@limiter.exempt
def archivesindex():
	return redirect("/archives/index.html")

@app.route('/archives/<path:path>')
@limiter.exempt
def archives(path):
	resp = make_response(send_from_directory('/archives', path))
	if request.path.endswith('.css'): resp.headers.add("Content-Type", "text/css")
	return resp

@app.route('/assets/<path:path>')
@limiter.exempt
def static_service(path):
	resp = make_response(send_from_directory('./assets', path))
	if request.path.endswith('.css'): resp.headers.add("Content-Type", "text/css")
	return resp

@app.get("/robots.txt")
def robots_txt():
	return send_file("./assets/robots.txt")

@app.get("/settings")
@auth_required
def settings(v):
	if v and v.is_banned and not v.unban_utc: return render_template("seized.html")

	return redirect("/settings/profile")


@app.get("/settings/profile")
@auth_required
def settings_profile(v):
	if v and v.is_banned and not v.unban_utc: return render_template("seized.html")

	return render_template("settings_profile.html",
						   v=v)


@app.get("/titles")
@auth_desired
def titles(v):
	if v and v.is_banned and not v.unban_utc: return render_template("seized.html")

	titles = [x for x in g.db.query(Title).order_by(text("id asc")).all()]
	return render_template("/titles.html",
						   v=v,
						   titles=titles)

@app.get("/badges")
@auth_desired
def badges(v):
	if v and v.is_banned and not v.unban_utc: return render_template("seized.html")

	badges = [
		x for x in g.db.query(BadgeDef).order_by(
			text("rank asc, id asc")).all()]
	return render_template("badges.html",
						   v=v,
						   badges=badges)

@app.get("/blocks")
@auth_desired
def blocks(v):
	if v and v.is_banned and not v.unban_utc: return render_template("seized.html")

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
	if v and v.is_banned and not v.unban_utc: return render_template("seized.html")

	users = [x for x in g.db.query(User).filter(User.is_banned > 0, User.unban_utc == 0).all()]
	return render_template("banned.html", v=v, users=users)

@app.get("/formatting")
@auth_desired
def formatting(v):
	if v and v.is_banned and not v.unban_utc: return render_template("seized.html")

	return render_template("formatting.html", v=v)
	
@app.get("/.well-known/brave-rewards-verification.txt")
def brave():
	with open(".well-known/brave-rewards-verification.txt", "r") as f: return Response(f.read(), mimetype='text/plain')

@app.get("/.well-known/assetlinks.json")
def googleplayapp():
	with open(".well-known/assetlinks.json", "r") as f: return Response(f.read(), mimetype='application/json')

@app.route("/service-worker.js")
def serviceworker():
	with open(".well-known/service-worker.js", "r") as f: return Response(f.read(), mimetype='application/javascript')


@app.get("/settings/security")
@auth_required
def settings_security(v):
	if v and v.is_banned and not v.unban_utc: return render_template("seized.html")

	return render_template("settings_security.html",
						   v=v,
						   mfa_secret=pyotp.random_base32() if not v.mfa_secret else None,
						   error=request.args.get("error") or None,
						   msg=request.args.get("msg") or None
						   )

@app.post("/dismiss_mobile_tip")
def dismiss_mobile_tip():

	session["tooltip_last_dismissed"]=int(time.time())
	session.modified=True

	return "", 204
