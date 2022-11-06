from urllib.parse import urlencode
from files.mail import *
from files.__main__ import app, limiter
from files.helpers.const import *
from files.helpers.strings import sql_ilike_clean
import requests

@app.get("/login")
@auth_desired
def login_get(v):

	redir = request.values.get("redirect")
	if redir:
		redir = redir.replace("/logged_out", "").strip()
		if not redir.startswith(f'{SITE_FULL}/') and not redir.startswith('/'): redir = None

	if v and redir:
		if redir.startswith(f'{SITE_FULL}/'): return redirect(redir)
		elif redir.startswith('/'): return redirect(f'{SITE_FULL}{redir}')

	return render_template("login.html", failed=False, redirect=redir)


def check_for_alts(current_id):
	ids = [x[0] for x in g.db.query(User.id).all()]
	past_accs = set(session.get("history", []))

	for past_id in list(past_accs):
		
		if past_id not in ids:
			past_accs.remove(past_id)
			continue

		if past_id == current_id: continue

		li = [past_id, current_id]
		existing = g.db.query(Alt).filter(Alt.user1.in_(li), Alt.user2.in_(li)).one_or_none()

		if not existing:
			new_alt = Alt(user1=past_id, user2=current_id)
			g.db.add(new_alt)
			g.db.flush()
			
		otheralts = g.db.query(Alt).filter(Alt.user1.in_(li), Alt.user2.in_(li)).all()
		for a in otheralts:
			if a.user1 != past_id:
				li = [a.user1, past_id]
				existing = g.db.query(Alt).filter(Alt.user1.in_(li), Alt.user2.in_(li)).one_or_none()
				if not existing:
					new_alt = Alt(user1=a.user1, user2=past_id)
					g.db.add(new_alt)
					g.db.flush()

			if a.user1 != current_id:
				li = [a.user1, current_id]
				existing = g.db.query(Alt).filter(Alt.user1.in_(li), Alt.user2.in_(li)).one_or_none()
				if not existing:
					new_alt = Alt(user1=a.user1, user2=current_id)
					g.db.add(new_alt)
					g.db.flush()

			if a.user2 != past_id:
				li = [a.user2, past_id]
				existing = g.db.query(Alt).filter(Alt.user1.in_(li), Alt.user2.in_(li)).one_or_none()
				if not existing:
					new_alt = Alt(user1=a.user2, user2=past_id)
					g.db.add(new_alt)
					g.db.flush()

			if a.user2 != current_id:
				li = [a.user2, current_id]
				existing = g.db.query(Alt).filter(Alt.user1.in_(li), Alt.user2.in_(li)).one_or_none()
				if not existing:
					new_alt = Alt(user1=a.user2, user2=current_id)
					g.db.add(new_alt)
					g.db.flush()
	
	past_accs.add(current_id)
	session["history"] = list(past_accs)


@app.post("/login")
@limiter.limit("1/second;6/minute;200/hour;1000/day")
def login_post():
	template = ''

	username = request.values.get("username")

	if not username: abort(400)
	username  = sql_ilike_clean(username.lstrip('@'))

	if not username: abort(400)
	if username.startswith('@'): username = username[1:]

	if "@" in username:
		try: account = g.db.query(User).filter(User.email.ilike(username)).one_or_none()
		except: return "Multiple users use this email!"
	else: account = get_user(username, graceful=True)

	if not account:
		time.sleep(random.uniform(0, 2))
		return render_template("login.html", failed=True)


	if request.values.get("password"):

		if not account.verifyPass(request.values.get("password")):
			time.sleep(random.uniform(0, 2))
			return render_template("login.html", failed=True)

		if account.mfa_secret:
			now = int(time.time())
			hash = generate_hash(f"{account.id}+{now}+2fachallenge")
			return render_template("login_2fa.html",
								   v=account,
								   time=now,
								   hash=hash,
								   redirect=request.values.get("redirect", "/")
								   )
	elif request.values.get("2fa_token", "x"):
		now = int(time.time())

		if now - int(request.values.get("time")) > 600:
			return redirect('/login')

		formhash = request.values.get("hash")
		if not validate_hash(f"{account.id}+{request.values.get('time')}+2fachallenge", formhash):
			return redirect("/login")

		if not account.validate_2fa(request.values.get("2fa_token", "").strip()):
			hash = generate_hash(f"{account.id}+{time}+2fachallenge")
			return render_template("login_2fa.html",
								   v=account,
								   time=now,
								   hash=hash,
								   failed=True,
								   )

	else:
		abort(400)

	session.permanent = True
	session["session_id"] = token_hex(49)
	session["lo_user"] = account.id
	session["login_nonce"] = account.login_nonce
	if account.id == OWNER_ID:
		session["verified"] = time.time()

	check_for_alts(account.id)

	g.db.commit()

	redir = request.values.get("redirect")
	if redir:
		redir = redir.replace("/logged_out", "").strip()
		if not redir.startswith(f'{SITE_FULL}/') and not redir.startswith('/'): redir = '/'

	if redir:
		if redir.startswith(f'{SITE_FULL}/'): return redirect(redir)
		if redir.startswith('/'): return redirect(f'{SITE_FULL}{redir}')
	return redirect('/')

@app.get("/me")
@app.get("/@me")
@auth_required
def me(v):
	if request.headers.get("Authorization"): return v.json
	else: return redirect(v.url)


@app.get("/logout")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def logout(v):

	session.pop("session_id", None)
	session.pop("lo_user", None)

	return redirect('/')


@app.get("/signup")
@auth_desired
def sign_up_get(v):
	if not app.config['SETTINGS']['Signups']:
		return {"error": "New account registration is currently closed. Please come back later."}, 403

	if v: return redirect(SITE_FULL)

	agent = request.headers.get("User-Agent")
	if not agent: abort(403)

	ref = request.values.get("ref")

	if ref:
		ref  = sql_ilike_clean(ref)
		ref_user = g.db.query(User).filter(User.username.ilike(ref)).one_or_none()

	else:
		ref_user = None

	if ref_user and (ref_user.id in session.get("history", [])):
		return render_template("sign_up_failed_ref.html")

	now = int(time.time())
	token = token_hex(16)
	session["signup_token"] = token

	formkey_hashstr = str(now) + token + agent

	formkey = hmac.new(key=bytes(environ.get("MASTER_KEY"), "utf-16"),
					   msg=bytes(formkey_hashstr, "utf-16"),
					   digestmod='md5'
					   ).hexdigest()

	error = request.values.get("error")

	return render_template("sign_up.html",
						   formkey=formkey,
						   now=now,
						   ref_user=ref_user,
						   hcaptcha=app.config["HCAPTCHA_SITEKEY"],
						   error=error
						   )


@app.post("/signup")
@limiter.limit("10/day")
@auth_desired
def sign_up_post(v):
	if not app.config['SETTINGS']['Signups']:
		return {"error": "New account registration is currently closed. Please come back later."}, 403

	if v: abort(403)

	agent = request.headers.get("User-Agent")
	if not agent: abort(403)

	form_timestamp = request.values.get("now", '0')
	form_formkey = request.values.get("formkey", "none")

	submitted_token = session.get("signup_token", "")
	if not submitted_token: abort(400)

	correct_formkey_hashstr = form_timestamp + submitted_token + agent

	correct_formkey = hmac.new(key=bytes(environ.get("MASTER_KEY"), "utf-16"),
								msg=bytes(correct_formkey_hashstr, "utf-16"),
								digestmod='md5'
							   ).hexdigest()

	now = int(time.time())

	username = request.values.get("username")
	
	if not username: abort(400)

	username = username.strip()

	def signup_error(error):

		args = {"error": error}
		if request.values.get("referred_by"):
			user = g.db.query(User).filter_by(id=request.values.get("referred_by")).one_or_none()
			if user: args["ref"] = user.username

		return redirect(f"/signup?{urlencode(args)}")

	if now - int(form_timestamp) < 5:
		return signup_error("There was a problem. Please try again.")

	if not hmac.compare_digest(correct_formkey, form_formkey):
		return signup_error("There was a problem. Please try again.")

	if not request.values.get(
			"password") == request.values.get("password_confirm"):
		return signup_error("Passwords did not match. Please try again.")

	if not valid_username_regex.fullmatch(username):
		return signup_error("Invalid username")

	if not valid_password_regex.fullmatch(request.values.get("password")):
		return signup_error("Password must be between 8 and 100 characters.")

	email = request.values.get("email").strip().lower()

	if email:
		if not email_regex.fullmatch(email):
			return signup_error("Invalid email.")
	else: email = None

	existing_account = get_user(username, graceful=True)
	if existing_account and existing_account.reserved:
		return redirect(existing_account.url)

	if existing_account:
		return signup_error("An account with that username already exists.")

	if app.config.get("HCAPTCHA_SITEKEY"):
		token = request.values.get("h-captcha-response")
		if not token:
			return signup_error("Unable to verify captcha [1].")

		data = {"secret": app.config["HCAPTCHA_SECRET"],
				"response": token,
				"sitekey": app.config["HCAPTCHA_SITEKEY"]}
		url = "https://hcaptcha.com/siteverify"

		x = requests.post(url, data=data, timeout=5)

		if not x.json()["success"]:
			return signup_error("Unable to verify captcha [2].")

	session.pop("signup_token")

	ref_id = int(request.values.get("referred_by", 0))

	id_1 = g.db.query(User.id).filter_by(id=9).count()
	users_count = g.db.query(User.id).count()
	if id_1 == 0 and users_count == 8:
		admin_level=3
		session["history"] = []
	else: admin_level=0

	profileurl = '/assets/images/default-profile-pic.webp'

	new_user = User(
		username=username,
		original_username = username,
		admin_level = admin_level,
		password=request.values.get("password"),
		email=email,
		referred_by=ref_id or None,
		ban_evade =  int(any((x.is_banned or x.shadowbanned) and not x.unban_utc for x in g.db.query(User).filter(User.id.in_(session.get("history", []))).all() if x)),
		profileurl=profileurl
	)

	g.db.add(new_user)
	g.db.flush()

	if ref_id:
		ref_user = g.db.query(User).filter_by(id=ref_id).one_or_none()

		if ref_user:
			if ref_user.referral_count and not ref_user.has_badge(10):
				new_badge = Badge(user_id=ref_user.id, badge_id=10)
				g.db.add(new_badge)
				g.db.flush()
				send_notification(ref_user.id, f"@AutoJanny has given you the following profile badge:\n\n![]({new_badge.path})\n\n{new_badge.name}")
			if ref_user.referral_count >= 10 and not ref_user.has_badge(11):
				new_badge = Badge(user_id=ref_user.id, badge_id=11)
				g.db.add(new_badge)
				g.db.flush()
				send_notification(ref_user.id, f"@AutoJanny has given you the following profile badge:\n\n![]({new_badge.path})\n\n{new_badge.name}")
			if ref_user.referral_count >= 100 and not ref_user.has_badge(12):
				new_badge = Badge(user_id=ref_user.id, badge_id=12)
				g.db.add(new_badge)
				g.db.flush()
				send_notification(ref_user.id, f"@AutoJanny has given you the following profile badge:\n\n![]({new_badge.path})\n\n{new_badge.name}")

	check_for_alts(new_user.id)

	if email: send_verification_email(new_user)

	send_notification(new_user.id, WELCOME_MSG)

	session.permanent = True
	session["session_id"] = token_hex(49)
	session["lo_user"] = new_user.id

	g.db.commit()

	return redirect(SITE_FULL)


@app.get("/forgot")
def get_forgot():
	return render_template("forgot_password.html")


@app.post("/forgot")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
def post_forgot():

	username = request.values.get("username")
	if not username: abort(400)

	email = request.values.get("email",'').strip().lower()

	if not email_regex.fullmatch(email):
		return render_template("forgot_password.html", error="Invalid email.")


	username  = sql_ilike_clean(username.lstrip('@'))
	email  = sql_ilike_clean(email)

	user = g.db.query(User).filter(
		User.username.ilike(username),
		User.email.ilike(email)).one_or_none()

	if user:
		now = int(time.time())
		token = generate_hash(f"{user.id}+{now}+forgot+{user.login_nonce}")
		url = f"{SITE_FULL}/reset?id={user.id}&time={now}&token={token}"

		send_mail(to_address=user.email,
				  subject="Password Reset Request",
				  html=render_template("email/password_reset.html",
									   action_url=url,
									   v=user)
				  )

	return render_template("forgot_password.html",
						   msg="If the username and email matches an account, you will be sent a password reset email. You have ten minutes to complete the password reset process.")


@app.get("/reset")
def get_reset():

	user_id = request.values.get("id")

	timestamp = int(request.values.get("time",0))
	token = request.values.get("token")

	now = int(time.time())

	if now - timestamp > 600:
		return render_template("message.html", 
			title="Password reset link expired",
			error="That password reset link has expired.")

	user = g.db.query(User).filter_by(id=user_id).one_or_none()
	
	if not user: abort(400)

	if not validate_hash(f"{user_id}+{timestamp}+forgot+{user.login_nonce}", token):
		abort(400)

	if not user:
		abort(404)

	reset_token = generate_hash(f"{user.id}+{timestamp}+reset+{user.login_nonce}")

	return render_template("reset_password.html",
						   v=user,
						   token=reset_token,
						   time=timestamp,
						   )


@app.post("/reset")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_desired
def post_reset(v):
	if v: return redirect('/')

	user_id = request.values.get("user_id")

	timestamp = int(request.values.get("time"))
	token = request.values.get("token")

	password = request.values.get("password")
	confirm_password = request.values.get("confirm_password")

	now = int(time.time())

	if now - timestamp > 600:
		return render_template("message.html",
							   title="Password reset expired",
							   error="That password reset form has expired.")

	user = g.db.query(User).filter_by(id=user_id).one_or_none()

	if not validate_hash(f"{user_id}+{timestamp}+reset+{user.login_nonce}", token):
		abort(400)
	if not user:
		abort(404)

	if password != confirm_password:
		return render_template("reset_password.html",
							   v=user,
							   token=token,
							   time=timestamp,
							   error="Passwords didn't match.")

	user.passhash = hash_password(password)
	g.db.add(user)

	g.db.commit()

	return render_template("message_success.html",
						   title="Password reset successful!",
						   message="Login normally to access your account.")

@app.get("/lost_2fa")
@auth_desired
def lost_2fa(v):

	return render_template(
		"lost_2fa.html",
		v=v
		)

@app.post("/request_2fa_disable")
@limiter.limit("1/second;6/minute;200/hour;1000/day")
def request_2fa_disable():

	username=request.values.get("username")
	user=get_user(username, graceful=True)
	if not user or not user.email or not user.mfa_secret:
		return render_template("message.html",
						   title="Removal request received",
						   message="If username, password, and email match, we will send you an email.")


	email=request.values.get("email").strip().lower()

	if not email_regex.fullmatch(email):
		return render_template("message.html", title="Invalid email.", error="Invalid email.")

	password =request.values.get("password")
	if not user.verifyPass(password):
		return render_template("message.html",
						   title="Removal request received",
						   message="If username, password, and email match, we will send you an email.")

	valid=int(time.time())
	token=generate_hash(f"{user.id}+{user.username}+disable2fa+{valid}+{user.mfa_secret}+{user.login_nonce}")

	action_url=f"{SITE_FULL}/reset_2fa?id={user.id}&t={valid}&token={token}"
	
	send_mail(to_address=user.email,
			  subject="2FA Removal Request",
			  html=render_template("email/2fa_remove.html",
								   action_url=action_url,
								   v=user)
			  )

	return render_template("message.html",
						   title="Removal request received",
						   message="If username, password, and email match, we will send you an email.")

@app.get("/reset_2fa")
def reset_2fa():

	now=int(time.time())
	t = request.values.get("t")
	if not t: abort(400)
	t = int(t)

	if now > t+3600*24:
		return render_template("message.html",
						   title="Expired Link",
						   error="That link has expired.")

	token=request.values.get("token")
	uid=request.values.get("id")

	user=get_account(uid)

	if not validate_hash(f"{user.id}+{user.username}+disable2fa+{t}+{user.mfa_secret}+{user.login_nonce}", token):
		abort(403)

	user.mfa_secret=None

	g.db.add(user)

	g.db.commit()

	return render_template("message_success.html",
						   title="Two-factor authentication removed.",
						   message="Login normally to access your account.")
