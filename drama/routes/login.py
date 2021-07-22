from urllib.parse import urlencode
from drama.mail import *
from drama.__main__ import app, limiter

valid_username_regex = re.compile("^[a-zA-Z0-9_\-]{3,25}$")
valid_password_regex = re.compile("^.{8,100}$")


@app.route("/login", methods=["GET"])
@no_cors
@auth_desired
def login_get(v):

	redir = request.args.get("redirect", "/")
	if v:
		return redirect(redir)

	return render_template("login.html",
						   failed=False,
						   i=random_image(),
						   redirect=redir)


def check_for_alts(current_id):
	# account history
	past_accs = set(session.get("history", []))
	past_accs.add(current_id)
	session["history"] = list(past_accs)

	# record alts
	for past_id in session["history"]:

		if past_id == current_id:
			continue

		check1 = g.db.query(Alt).filter_by(
			user1=current_id, user2=past_id).first()
		check2 = g.db.query(Alt).filter_by(
			user1=past_id, user2=current_id).first()

		if not check1 and not check2:

			try:
				new_alt = Alt(user1=past_id,
							  user2=current_id)
				g.db.add(new_alt)

			except BaseException:
				pass

# login post procedure


@no_cors
@app.route("/login", methods=["POST"])
@limiter.limit("6/minute")
def login_post():

	username = request.form.get("username")

	if "@" in username:
		account = g.db.query(User).filter(
			User.email.ilike(username),
			User.is_deleted == False).first()
	else:
		account = get_user(username, graceful=True)

	if not account:
		time.sleep(random.uniform(0, 2))
		return render_template("login.html", failed=True, i=random_image())

	if account.is_deleted:
		time.sleep(random.uniform(0, 2))
		return render_template("login.html", failed=True, i=random_image())

	# test password

	if request.form.get("password"):

		if not account.verifyPass(request.form.get("password")):
			time.sleep(random.uniform(0, 2))
			return render_template("login.html", failed=True, i=random_image())

		if account.mfa_secret:
			now = int(time.time())
			hash = generate_hash(f"{account.id}+{now}+2fachallenge")
			return render_template("login_2fa.html",
								   v=account,
								   time=now,
								   hash=hash,
								   i=random_image(),
								   redirect=request.form.get("redirect", "/")
								   )
	elif request.form.get("2fa_token", "x"):
		now = int(time.time())

		if now - int(request.form.get("time")) > 600:
			return redirect('/login')

		formhash = request.form.get("hash")
		if not validate_hash(f"{account.id}+{request.form.get('time')}+2fachallenge",
							 formhash
							 ):
			return redirect("/login")

		if not account.validate_2fa(request.form.get("2fa_token", "").strip()):
			hash = generate_hash(f"{account.id}+{time}+2fachallenge")
			return render_template("login_2fa.html",
								   v=account,
								   time=now,
								   hash=hash,
								   failed=True,
								   i=random_image()
								   )

	else:
		abort(400)

	if account.is_banned and account.unban_utc > 0 and time.time() > account.unban_utc:
		account.unban()

	# set session and user id
	session["user_id"] = account.id
	session["session_id"] = token_hex(16)
	session["login_nonce"] = account.login_nonce
	session.permanent = True

	check_for_alts(account.id)

	account.refresh_selfset_badges()

	# check for previous page

	redir = request.form.get("redirect", "/")
	if redir:
		return redirect(redir)
	else:
		return redirect(account.url)


@app.route("/me", methods=["GET"])
@auth_required
def me(v):
	return redirect(v.url)


@app.route("/logout", methods=["POST"])
@auth_required
@validate_formkey
def logout(v):

	session.pop("user_id", None)
	session.pop("session_id", None)

	return "", 204

# signing up


@app.route("/signup", methods=["GET"])
@no_cors
@auth_desired
def sign_up_get(v):
	board = g.db.query(Board).filter_by(id=1).first()
	if board.disablesignups: return "Signups are disable for the time being.", 403

	if v:
		return redirect("/")

	agent = request.headers.get("User-Agent", None)
	if not agent:
		abort(403)

	# check for referral in link
	ref_id = None
	ref = request.args.get("ref", None)
	if ref:
		ref_user = g.db.query(User).filter(User.username.ilike(ref)).first()

	else:
		ref_user = None

	if ref_user and (ref_user.id in session.get("history", [])):
		return render_template("sign_up_failed_ref.html",
							   i=random_image())

	# check tor
	# if request.headers.get("CF-IPCountry")=="T1":
	#	return render_template("sign_up_tor.html",
	#		i=random_image(),
	#		ref_user=ref_user)

	# Make a unique form key valid for one account creation
	now = int(time.time())
	token = token_hex(16)
	session["signup_token"] = token
	ip = request.remote_addr

	formkey_hashstr = str(now) + token + agent

	# formkey is a hash of session token, timestamp, and IP address
	formkey = hmac.new(key=bytes(environ.get("MASTER_KEY"), "utf-16"),
					   msg=bytes(formkey_hashstr, "utf-16"),
					   digestmod='md5'
					   ).hexdigest()

	redir = request.args.get("redirect", None)

	error = request.args.get("error", None)

	return render_template("sign_up.html",
						   formkey=formkey,
						   now=now,
						   i=random_image(),
						   redirect=redir,
						   ref_user=ref_user,
						   error=error,
						   hcaptcha=app.config["HCAPTCHA_SITEKEY"]
						   )

# signup api


@app.route("/signup", methods=["POST"])
@no_cors
@auth_desired
def sign_up_post(v):
	board = g.db.query(Board).filter_by(id=1).first()
	if board.disablesignups: return "Signups are disable for the time being.", 403

	if v:
		abort(403)

	agent = request.headers.get("User-Agent", None)
	if not agent:
		abort(403)

	# check tor
	# if request.headers.get("CF-IPCountry")=="T1":
	#	return render_template("sign_up_tor.html",
	#		i=random_image()
	#	)

	form_timestamp = request.form.get("now", '0')
	form_formkey = request.form.get("formkey", "none")

	submitted_token = session.get("signup_token", "")
	if not submitted_token:
		abort(400)

	correct_formkey_hashstr = form_timestamp + submitted_token + agent

	correct_formkey = hmac.new(key=bytes(environ.get("MASTER_KEY"), "utf-16"),
								msg=bytes(correct_formkey_hashstr, "utf-16"),
								digestmod='md5'
							   ).hexdigest()

	now = int(time.time())

	username = request.form.get("username")

	# define function that takes an error message and generates a new signup
	# form
	def new_signup(error):

		args = {"error": error}
		if request.form.get("referred_by"):
			user = g.db.query(User).filter_by(
				id=request.form.get("referred_by")).first()
			if user:
				args["ref"] = user.username

		return redirect(f"/signup?{urlencode(args)}")

	if app.config["DISABLE_SIGNUPS"]:
		return new_signup("New account registration is currently closed. Please come back later.")

	if now - int(form_timestamp) < 5:
		#print(f"signup fail - {username } - too fast")
		return new_signup("There was a problem. Please try again.")

	if not hmac.compare_digest(correct_formkey, form_formkey):
		#print(f"signup fail - {username } - mismatched formkeys")
		return new_signup("There was a problem. Please try again.")

	# check for matched passwords
	if not request.form.get(
			"password") == request.form.get("password_confirm"):
		return new_signup("Passwords did not match. Please try again.")

	# check username/pass conditions
	if not re.match(valid_username_regex, request.form.get("username")):
		#print(f"signup fail - {username } - mismatched passwords")
		return new_signup("Invalid username")

	if not re.match(valid_password_regex, request.form.get("password")):
		#print(f"signup fail - {username } - invalid password")
		return new_signup("Password must be between 8 and 100 characters.")

	# if not re.match(valid_email_regex, request.form.get("email")):
	#	return new_signup("That's not a valid email.")

	# Check for existing accounts
	email = request.form.get("email")
	email = email.strip()
	if not email:
		email = None

	#counteract gmail username+2 and extra period tricks - convert submitted email to actual inbox
	if email and email.endswith("@gmail.com"):
		gmail_username=email.split('@')[0]
		gmail_username=gmail_username.split('+')[0]
		gmail_username=gmail_username.replace('.','')
		email=f"{gmail_username}@gmail.com"


	existing_account = get_user(request.form.get("username"), graceful=True)
	if existing_account and existing_account.reserved:
		return redirect(existing_account.permalink)

	if existing_account or (email and g.db.query(
			User).filter(User.email.ilike(email)).first()):
		# #print(f"signup fail - {username } - email already exists")
		return new_signup(
			"An account with that username or email already exists.")

	# check bot
	if app.config.get("HCAPTCHA_SITEKEY"):
		token = request.form.get("h-captcha-response")
		if not token:
			return new_signup("Unable to verify captcha [1].")

		data = {"secret": app.config["HCAPTCHA_SECRET"],
				"response": token,
				"sitekey": app.config["HCAPTCHA_SITEKEY"]}
		url = "https://hcaptcha.com/siteverify"

		x = requests.post(url, data=data)

		if not x.json()["success"]:
			#print(x.json())
			return new_signup("Unable to verify captcha [2].")

	# kill tokens
	session.pop("signup_token")

	# get referral
	ref_id = int(request.form.get("referred_by", 0))

	# upgrade user badge
	if ref_id:
		ref_user = g.db.query(User).options(
			lazyload('*')).filter_by(id=ref_id).first()
		if ref_user:
			ref_user.refresh_selfset_badges()
			g.db.add(ref_user)

	# make new user
	try:
		new_user = User(
			username=username,
			original_username = username,
			password=request.form.get("password"),
			email=email,
			created_utc=int(time.time()),
			creation_ip=request.remote_addr,
			referred_by=ref_id or None,
			tos_agreed_utc=int(time.time()),
			creation_region=request.headers.get("cf-ipcountry"),
			ban_evade =  int(any([x.is_banned for x in g.db.query(User).filter(User.id.in_(tuple(session.get("history", [])))).all() if x]))
			)

	except Exception as e:
		#print(e)
		return new_signup("Please enter a valid email")

	g.db.add(new_user)
	g.db.commit()

	# give a beta badge
	beta_badge = Badge(user_id=new_user.id,
					   badge_id=6)

	g.db.add(beta_badge)

	# check alts

	check_for_alts(new_user.id)

	# send welcome/verify email
	if email:
		send_verification_email(new_user)

	# send welcome message
	send_notification(1046, new_user, "Dude bussy lmao")

	session["user_id"] = new_user.id
	session["session_id"] = token_hex(16)

	redir = request.form.get("redirect", None)

	# #print(f"Signup event: @{new_user.username}")

	return redirect("/")


@app.route("/forgot", methods=["GET"])
def get_forgot():

	return render_template("forgot_password.html",
						   i=random_image()
						   )


@app.route("/forgot", methods=["POST"])
def post_forgot():

	username = request.form.get("username").lstrip('@')
	email = request.form.get("email",'').strip()

	email=email.replace("_","\_").replace(".","")

	user = g.db.query(User).filter(
		User.username.ilike(username),
		User.email.ilike(email),
		User.is_deleted == False).first()

	if user:
		# generate url
		now = int(time.time())
		token = generate_hash(f"{user.id}+{now}+forgot+{user.login_nonce}")
		url = f"https://{app.config['SERVER_NAME']}/reset?id={user.id}&time={now}&token={token}"

		send_mail(to_address=user.email,
				  subject="Drama - Password Reset Request",
				  html=render_template("email/password_reset.html",
									   action_url=url,
									   v=user)
				  )

	return render_template("forgot_password.html",
						   msg="If the username and email matches an account, you will be sent a password reset email. You have ten minutes to complete the password reset process.",
						   i=random_image())


@app.route("/reset", methods=["GET"])
def get_reset():

	user_id = request.args.get("id")
	timestamp = int(request.args.get("time",0))
	token = request.args.get("token")

	now = int(time.time())

	if now - timestamp > 600:
		return render_template("message.html", 
			title="Password reset link expired",
			error="That password reset link has expired.")

	user = g.db.query(User).filter_by(id=user_id).first()

	if not validate_hash(f"{user_id}+{timestamp}+forgot+{user.login_nonce}", token):
		abort(400)

	if not user:
		abort(404)

	reset_token = generate_hash(f"{user.id}+{timestamp}+reset+{user.login_nonce}")

	return render_template("reset_password.html",
						   v=user,
						   token=reset_token,
						   time=timestamp,
						   i=random_image()
						   )


@app.route("/reset", methods=["POST"])
@auth_desired
def post_reset(v):
	if v:
		return redirect('/')

	user_id = request.form.get("user_id")
	timestamp = int(request.form.get("time"))
	token = request.form.get("token")

	password = request.form.get("password")
	confirm_password = request.form.get("confirm_password")

	now = int(time.time())

	if now - timestamp > 600:
		return render_template("message.html",
							   title="Password reset expired",
							   error="That password reset form has expired.")

	user = g.db.query(User).filter_by(id=user_id).first()

	if not validate_hash(f"{user_id}+{timestamp}+reset+{user.login_nonce}", token):
		abort(400)
	if not user:
		abort(404)

	if not password == confirm_password:
		return render_template("reset_password.html",
							   v=user,
							   token=token,
							   time=timestamp,
							   i=random_image(),
							   error="Passwords didn't match.")

	user.passhash = hash_password(password)
	g.db.add(user)

	return render_template("message_success.html",
						   title="Password reset successful!",
						   message="Login normally to access your account.")

@app.route("/lost_2fa")
@auth_desired
def lost_2fa(v):

	return render_template(
		"lost_2fa.html",
		i=random_image(),
		v=v
		)

@app.route("/request_2fa_disable", methods=["POST"])
@limiter.limit("6/minute")
def request_2fa_disable():

	username=request.form.get("username")
	user=get_user(username, graceful=True)
	if not user or not user.email or not user.mfa_secret:
		return render_template("message.html",
						   title="Removal request received",
						   message="If username, password, and email match, we will send you an email.")


	email=request.form.get("email")
	if email and email.endswith("@gmail.com"):
		gmail_username=email.split('@')[0]
		gmail_username=gmail_username.split('+')[0]
		gmail_username=gmail_username.replace('.','')
		email=f"{gmail_username}@gmail.com"

	if email != user.email:
		return render_template("message.html",
						   title="Removal request received",
						   message="If username, password, and email match, we will send you an email.")


	password =request.form.get("password")
	if not user.verifyPass(password):
		return render_template("message.html",
						   title="Removal request received",
						   message="If username, password, and email match, we will send you an email.")

	#compute token
	valid=int(time.time())+60*60*24*3
	token=generate_hash(f"{user.id}+{user.username}+disable2fa+{valid}+{user.mfa_secret}+{user.login_nonce}")

	action_url=f"https://{app.config['SERVER_NAME']}/reset_2fa?id={user.base36id}&t={valid}&token={token}"
	
	send_mail(to_address=user.email,
			  subject="Drama - 2FA Removal Request",
			  html=render_template("email/2fa_remove.html",
								   action_url=action_url,
								   v=user)
			  )

	return render_template("message.html",
						   title="Removal request received",
						   message="If username, password, and email match, we will send you an email.")

@app.route("/reset_2fa", methods=["GET"])
def reset_2fa():

	now=int(time.time())
	t=int(request.args.get("t"))

	if now<t:
		return render_template("message.html",
						   title="Inactive Link",
						   error="That link isn't active yet. Try again later.")
	elif now > t+3600*24:
		return render_template("message.html",
						   title="Expired Link",
						   error="That link has expired.")

	token=request.args.get("token")
	uid=request.args.get("id")

	user=get_account(uid)

	if not validate_hash(f"{user.id}+{user.username}+disable2fa+{t}+{user.mfa_secret}+{user.login_nonce}", token):
		abort(403)

	#validation successful, remove 2fa
	user.mfa_secret=None

	g.db.add(user)
	g.db.commit()

	return render_template("message_success.html",
						   title="Two-factor authentication removed.",
						   message="Login normally to access your account.")
