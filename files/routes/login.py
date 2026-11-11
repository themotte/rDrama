from urllib.parse import urlencode

from sqlalchemy import and_, or_
from sqlalchemy.exc import MultipleResultsFound

from files.helpers.config.environment import WELCOME_MSG
from files.mail import *
from files.__main__ import app, limiter
from files.helpers.config.const import *
from files.helpers.captcha import validate_captcha

def _redirect_target():
	'''Where the "redirect" parameter asks to go after logging in, as an absolute URL on this site with any "/logged_out" removed, or None when it names no page here.'''
	redir = (request.values.get("redirect") or "").replace("/logged_out", "").strip()
	if redir.startswith('/'): redir = SITE_FULL + redir
	return redir if redir.startswith(f'{SITE_FULL}/') else None


@app.get("/login")
@auth_desired
def login_get(v):
	redir = _redirect_target()
	if v and redir: return redirect(redir)

	return render_template("login/login.html", failed=False, redirect=redir)


def check_for_alts(current_id):
	'''Records the accounts this browser logged into before as alts of `current_id`, and adds it to the browser's history.'''
	history = list(dict.fromkeys(session.get("history", [])))
	live = {id for (id,) in g.db.query(User.id).filter(User.id.in_(history))} if history else set()
	history = [id for id in history if id in live]

	for past_id in history:
		if past_id == current_id: continue
		pair = or_(and_(Alt.user1 == past_id, Alt.user2 == current_id), and_(Alt.user1 == current_id, Alt.user2 == past_id))
		if not g.db.query(Alt).filter(pair).first():
			g.db.add(Alt(user1=past_id, user2=current_id))

	if current_id not in history: history.append(current_id)
	session["history"] = history


@app.post("/login")
@limiter.limit("1/second;6/minute;200/hour;1000/day")
def login_post():
	username = request.values.get("username")

	if not username: abort(400)
	if username.startswith('@'): username = username[1:]

	if "@" in username:
		try: account = g.db.query(User).filter(func.lower(User.email) == username.lower()).one_or_none()
		except MultipleResultsFound: return "Multiple users use this email!"
	else: account = get_user(username, graceful=True)

	if not account:
		time.sleep(random.uniform(0, 2))
		return render_template("login/login.html", failed=True)

	if request.values.get("password"):

		if not account.verifyPass(request.values.get("password")):
			time.sleep(random.uniform(0, 2))
			return render_template("login/login.html", failed=True)

		if account.mfa_secret:
			now = int(time.time())
			hash = token_sign("2fa-challenge", account.id, now, account.login_nonce)
			return render_template("login/login_2fa.html",
								   v=account,
								   time=now,
								   hash=hash,
								   redirect=request.values.get("redirect", "/")
								   )
	else:
		try: challenge_time = int(request.values.get("time", ""))
		except ValueError: abort(400, "A login needs a password or a 2FA challenge.")

		if not token_fresh(challenge_time, 600):
			return redirect('/login')

		if not token_verify("2fa-challenge", request.values.get("hash"), account.id, challenge_time, account.login_nonce):
			return redirect("/login")

		if not account.validate_2fa(request.values.get("2fa_token", "").strip()):
			return render_template("login/login_2fa.html",
								   v=account,
								   time=challenge_time,
								   hash=request.values.get("hash"),
								   redirect=request.values.get("redirect", "/"),
								   failed=True,
								   )

	session.permanent = True
	session["session_id"] = token_hex(49)
	session["lo_user"] = account.id
	session["login_nonce"] = account.login_nonce

	check_for_alts(account.id)

	g.db.commit()

	return redirect(_redirect_target() or '/')

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
		abort(403, "New account registration is currently closed. Please come back later.")

	if v: return redirect(SITE_FULL)

	agent = request.headers.get("User-Agent")

	ref = request.values.get("ref")

	if ref:
		ref_user = g.db.query(User).filter(func.lower(User.username) == ref.lower()).one_or_none()

	else:
		ref_user = None

	if ref_user and (ref_user.id in session.get("history", [])):
		return render_template("login/sign_up_failed_ref.html")

	now = int(limiter.clock())
	token = token_hex(16)
	session["signup_token"] = token

	formkey = token_sign("signup", now, token, agent)

	error = request.values.get("error")

	return render_template(
		"login/sign_up.html",
		formkey=formkey,
		now=now,
		ref_user=ref_user,
		error=error
	)


@app.post("/signup")
@limiter.limit("10/day")
@auth_desired
def sign_up_post(v):
	if not app.config['SETTINGS']['Signups']:
		abort(403, "New account registration is currently closed. Please come back later.")

	if v: abort(403)

	agent = request.headers.get("User-Agent")

	form_timestamp = request.values.get("now", '0')
	form_formkey = request.values.get("formkey", "none")

	submitted_token = session.get("signup_token", "")
	if not submitted_token: abort(400)

	now = int(limiter.clock())

	username = request.values.get("usernametwo")
	
	if not username: abort(400)

	username = username.strip()

	ref_user = None
	if "referred_by" in request.values:
		ref_id = parse_id(request.values.get("referred_by"))
		ref_user = g.db.get(User, ref_id) if ref_id is not None else None
		if not ref_user: abort(400, "That referral names no account.")

	def signup_error(error):
		args = {"error": error}
		if ref_user: args["ref"] = ref_user.username

		return redirect(f"/signup?{urlencode(args)}")

	if limiter.enabled:
		try: form_age = now - int(form_timestamp)
		except ValueError: form_age = 0
		if form_age < 5:
			return signup_error("There was a problem. Please try again.")

	if not token_verify("signup", form_formkey, form_timestamp, submitted_token, agent):
		return signup_error("There was a problem. Please try again.")

	password = request.values.get("password") or ""
	if password != (request.values.get("password_confirm") or ""):
		return signup_error("Passwords did not match. Please try again.")

	if not valid_username_regex.fullmatch(username):
		return signup_error("Invalid username")

	if not valid_password_regex.fullmatch(password):
		return signup_error("Password must be between 8 and 100 characters.")

	email = (request.values.get("email") or "").strip().lower()

	if email:
		if not email_regex.fullmatch(email):
			return signup_error("Invalid email.")
	else: email = None

	existing_account = get_user(username, graceful=True)
	if existing_account and existing_account.reserved:
		return redirect(existing_account.url)

	if existing_account:
		return signup_error("An account with that username already exists.")
	
	if not validate_captcha(request.values.get("h-captcha-response", "")):
		return signup_error("Unable to verify CAPTCHA")

	session.pop("signup_token")

	# The first account on a fresh site runs it.
	if not g.db.query(User.id).filter(User.id.notin_(SYSTEM_ACCOUNT_IDS)).first():
		admin_level=3
		session["history"] = []
	else: admin_level=0

	profileurl = '/assets/images/default-profile-pic.webp'

	new_user = User(
		username=username,
		original_username = username,
		admin_level = admin_level,
		password=password,
		email=email,
		referred_by=ref_user.id if ref_user else None,
		ban_evade =  int(any((x.is_banned or x.shadowbanned) and not x.unban_utc for x in g.db.query(User).filter(User.id.in_(session.get("history", []))).all() if x)),
		profileurl=profileurl
	)

	g.db.add(new_user)
	g.db.flush()

	check_for_alts(new_user.id)

	if email: send_verification_email(new_user)

	send_notification(new_user.id, WELCOME_MSG)

	session.permanent = True
	session["session_id"] = token_hex(49)
	session["lo_user"] = new_user.id
	session["login_nonce"] = new_user.login_nonce

	g.db.commit()

	return redirect(SITE_FULL)


@app.get("/forgot")
def get_forgot():
	return render_template("login/forgot_password.html")


@app.post("/forgot")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
def post_forgot():
	username = request.values.get("username")
	if not username: abort(400)

	email = request.values.get("email",'').strip().lower()

	if not email_regex.fullmatch(email):
		return render_template("login/forgot_password.html", error="Invalid email.")

	username  = username.lstrip('@')

	user = g.db.query(User).filter(
		func.lower(User.username) == username.lower(),
		func.lower(User.email) == email.lower()).one_or_none()

	if user:
		now = int(time.time())
		token = token_sign("forgot", user.id, now, user.login_nonce)
		url = f"{SITE_FULL}/reset?id={user.id}&time={now}&token={token}"

		send_mail(to_address=user.email,
				  subject="Password Reset Request",
				  html=render_template("email/password_reset.html",
									   action_url=url,
									   v=user)
				  )

	return render_template("login/forgot_password.html",
						   msg="If the username and email matches an account, you will be sent a password reset email. You have ten minutes to complete the password reset process.")


@app.get("/reset")
def get_reset():
	user_id = parse_id(request.values.get("id"))
	timestamp = request.values.get("time", type=int)
	token = request.values.get("token")
	if user_id is None or timestamp is None: abort(400)

	if not token_fresh(timestamp, 600):
		return render_template("message.html", 
			title="Password reset link expired",
			error="That password reset link has expired.")

	user = g.db.query(User).filter_by(id=user_id).one_or_none()
	
	if not user: abort(400)

	if not token_verify("forgot", token, user_id, timestamp, user.login_nonce):
		abort(400)

	reset_token = token_sign("reset", user.id, timestamp, user.login_nonce)

	return render_template("login/reset_password.html",
						   v=user,
						   token=reset_token,
						   time=timestamp,
						   )


@app.post("/reset")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_desired
def post_reset(v):
	if v: return redirect('/')

	user_id = parse_id(request.values.get("user_id"))
	timestamp = request.values.get("time", type=int)
	token = request.values.get("token")

	password = request.values.get("password")
	confirm_password = request.values.get("confirm_password")
	if user_id is None or timestamp is None or password is None: abort(400)

	if not token_fresh(timestamp, 600):
		return render_template("message.html",
							   title="Password reset expired",
							   error="That password reset form has expired.")

	user = g.db.get(User, user_id)

	if not user or not token_verify("reset", token, user_id, timestamp, user.login_nonce):
		abort(400)

	if password != confirm_password:
		return render_template("login/reset_password.html",
							   v=user,
							   token=token,
							   time=timestamp,
							   error="Passwords didn't match.")

	if not valid_password_regex.fullmatch(password):
		return render_template("login/reset_password.html",
							   v=user,
							   token=token,
							   time=timestamp,
							   error="Password must be between 8 and 100 characters.")

	user.passhash = user.hash_password(password)
	user.sign_out_everywhere()
	g.db.add(user)

	g.db.commit()

	return render_template("message_success.html",
						   title="Password reset successful!",
						   message="Login normally to access your account.")

@app.get("/lost_2fa")
@auth_desired
def lost_2fa(v):
	return render_template(
		"login/lost_2fa.html",
		v=v
		)

@app.post("/request_2fa_disable")
@limiter.limit("1/second;6/minute;200/hour;1000/day")
def request_2fa_disable():
	email=(request.values.get("email") or "").strip().lower()

	if not email_regex.fullmatch(email):
		return render_template("message.html", title="Invalid email.", error="Invalid email.")

	user=get_user(request.values.get("username"), graceful=True)

	if not user or not user.email or not user.mfa_secret or not user.verifyPass(request.values.get("password") or "") or user.email.lower() != email:
		return render_template("message.html",
						   title="Removal request received",
						   message="If username, password, and email match, we will send you an email.")

	valid=int(time.time())
	token=token_sign("2fa-remove", user.id, user.username, valid, user.mfa_secret, user.login_nonce)

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

# A 2FA removal link starts working this long after it's sent, so an owner who didn't ask for it has time to read the mail and cancel it by changing the password, and keeps working for a day after that.
TWO_FACTOR_REMOVAL_DELAY = 72 * 3600
TWO_FACTOR_REMOVAL_WINDOW = 24 * 3600


def _removal_link_account():
	'''The account a 2FA removal link (its id, t and token) names. Any other link ends the request with the page refusing it.'''
	t = request.values.get("t", type=int)
	if t is None: abort(400)

	if int(time.time()) < t + TWO_FACTOR_REMOVAL_DELAY:
		abort(make_response(render_template("message.html",
						   title="Not Yet",
						   error="That link starts working 72 hours after it was sent.")))

	if not token_fresh(t, TWO_FACTOR_REMOVAL_DELAY + TWO_FACTOR_REMOVAL_WINDOW):
		abort(make_response(render_template("message.html",
						   title="Expired Link",
						   error="That link has expired.")))

	user = get_account(request.values.get("id"))

	if not user.mfa_secret or not token_verify("2fa-remove", request.values.get("token"), user.id, user.username, t, user.mfa_secret, user.login_nonce):
		abort(403)

	return user


@app.get("/reset_2fa")
def reset_2fa_confirm():
	user = _removal_link_account()

	return render_template("login/reset_2fa.html", user=user, t=request.values.get("t"), token=request.values.get("token"))


@app.post("/reset_2fa")
@limiter.limit("1/second;6/minute;200/hour;1000/day")
def reset_2fa():
	user = _removal_link_account()

	user.mfa_secret=None

	g.db.add(user)

	g.db.commit()

	return render_template("message_success.html",
						   title="Two-factor authentication removed.",
						   message="Login normally to access your account.")
