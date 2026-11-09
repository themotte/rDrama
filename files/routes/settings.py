from shutil import copyfile

from files.__main__ import app, limiter
from files.helpers.alerts import *
from files.helpers.config.const import *
from files.helpers.media import delete_uploaded_image, new_image_path, process_image
from files.helpers.sanitize import *
from files.helpers.sanitize import filter_emojis_only
from files.mail import *


@app.post("/settings/profile")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def settings_profile_post(v):
	updated = False
	# Image uploads are refused through Tor
	upload = request.files.get('file') if request.headers.get("cf-ipcountry") != "T1" else None

	if request.values.get("hidevotedon", v.hidevotedon) != v.hidevotedon:
		updated = True
		v.hidevotedon = request.values.get("hidevotedon") == 'true'

	elif request.values.get("cardview", v.cardview) != v.cardview:
		updated = True
		v.cardview = request.values.get("cardview") == 'true'

	elif request.values.get("highlightcomments", v.highlightcomments) != v.highlightcomments:
		updated = True
		v.highlightcomments = request.values.get("highlightcomments") == 'true'

	elif request.values.get("newtab", v.newtab) != v.newtab:
		updated = True
		v.newtab = request.values.get("newtab") == 'true'

	elif request.values.get("newtabexternal", v.newtabexternal) != v.newtabexternal:
		updated = True
		v.newtabexternal = request.values.get("newtabexternal") == 'true'

	elif request.values.get("over18", v.over_18) != v.over_18:
		updated = True
		v.over_18 = request.values.get("over18") == 'true'

	elif request.values.get("nofollow", v.is_nofollow) != v.is_nofollow:
		updated = True
		v.is_nofollow = request.values.get("nofollow") == 'true'

	elif request.values.get("bio") == "" and not upload:
		refuse_while_suspended(v)
		v.bio = None
		v.bio_html = None
		g.db.add(v)
		g.db.commit()
		return render_template("settings_profile.html", v=v, msg="Your bio has been updated.")

	elif request.values.get("friends") == "":
		refuse_while_suspended(v)
		v.friends = None
		v.friends_html = None
		g.db.add(v)
		g.db.commit()
		return render_template("settings_profile.html", v=v, msg="Your friends list has been updated.")

	elif request.values.get("friends"):
		refuse_while_suspended(v)
		friends = request.values.get("friends")[:500]

		friends_html = sanitize(friends)

		notify_users = NOTIFY_USERS(friends, v)

		if notify_users:
			cid = notif_comment(f"@{v.username} has added you to their friends list!")
			for x in notify_users:
				add_notif(cid, x)

		v.friends = friends[:500]
		v.friends_html=friends_html
		g.db.add(v)
		g.db.commit()
		return render_template("settings_profile.html",
							   v=v,
							   msg="Your friends list has been updated.")


	elif request.values.get("bio") or upload:
		refuse_while_suspended(v)
		bio = (request.values.get("bio") or "")[:1500]

		if upload:
			if (upload.content_type or '').startswith('image/'):
				name = new_image_path()
				upload.save(name)
				image = f"\n\n![]({process_image(name)})"
				# The text yields room so the image always fits the column
				bio = bio[:1500 - len(image)] + image
			else:
				if request.headers.get("Authorization") or request.headers.get("xhr"): abort(400, "Image files only")
				return render_template("settings_profile.html", v=v, error="Image files only"), 400
		
		bio_html = sanitize(bio)

		v.bio = bio
		v.bio_html=bio_html
		g.db.add(v)
		g.db.commit()
		return render_template("settings_profile.html",
							   v=v,
							   msg="Your bio has been updated.")


	frontsize = request.values.get("frontsize")
	if frontsize:
		if frontsize in {"15", "25", "50", "100"}:
			v.frontsize = int(frontsize)
			updated = True
		else: abort(400)

	defaultsortingcomments = request.values.get("defaultsortingcomments")
	if defaultsortingcomments:
		if defaultsortingcomments in SORTS_COMMENTS:
			v.defaultsortingcomments = defaultsortingcomments
			updated = True
		else: abort(400)

	defaultsorting = request.values.get("defaultsorting")
	if defaultsorting:
		if defaultsorting in SORTS_POSTS:
			v.defaultsorting = defaultsorting
			updated = True
		else: abort(400)

	theme = request.values.get("theme")
	if theme:
		if theme in THEMES:
			v.theme = theme
			if theme == "win98": 
				v.themecolor = "30409f"
			else:
				v.themecolor = "fff"
			updated = True
		else: abort(400)

	if updated:
		g.db.add(v)
		g.db.commit()

		return {"message": "Your settings have been updated."}

	else:
		abort(400, "You didn't change anything.")


@app.post("/settings/filters")
@auth_required
def filters(v):
	filters=request.values["filters"][:1000].strip()

	if filters == v.custom_filter_list:
		return render_template("settings_filters.html", v=v, error="You didn't change anything")

	v.custom_filter_list=filters
	g.db.add(v)
	g.db.commit()
	return render_template("settings_filters.html", v=v, msg="Your custom filters have been updated.")

@app.post("/changelogsub")
@auth_required
def changelogsub(v):
	v.changelogsub = not v.changelogsub
	g.db.add(v)

	g.db.commit()
	if v.changelogsub: return {"message": "You have subscribed to the changelog!"}
	else: return {"message": "You have unsubscribed from the changelog!"}

@app.post("/settings/namecolor")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def namecolor(v):
	refuse_while_suspended(v)
	color = str(request.values.get("color", "")).strip()
	if color.startswith('#'): color = color[1:]
	if len(color) != 6: return render_template("settings_security.html", v=v, error="Invalid color code")
	v.namecolor = color
	g.db.add(v)
	g.db.commit()
	return redirect("/settings/profile")
	
@app.post("/settings/themecolor")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def themecolor(v):
	themecolor = str(request.values.get("themecolor", "")).strip()
	if themecolor.startswith('#'): themecolor = themecolor[1:]
	if len(themecolor) != 6: return render_template("settings_security.html", v=v, error="Invalid color code")
	v.themecolor = themecolor
	g.db.add(v)
	g.db.commit()
	return redirect("/settings/profile")

@app.post("/settings/titlecolor")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def titlecolor(v):
	refuse_while_suspended(v)
	titlecolor = str(request.values.get("titlecolor", "")).strip()
	if titlecolor.startswith('#'): titlecolor = titlecolor[1:]
	if len(titlecolor) != 6: return render_template("settings_profile.html", v=v, error="Invalid color code")
	v.titlecolor = titlecolor
	g.db.add(v)
	g.db.commit()
	return redirect("/settings/profile")

@app.post("/settings/verifiedcolor")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def verifiedcolor(v):
	refuse_while_suspended(v)
	verifiedcolor = str(request.values.get("verifiedcolor", "")).strip()
	if verifiedcolor.startswith('#'): verifiedcolor = verifiedcolor[1:]
	if len(verifiedcolor) != 6: return render_template("settings_profile.html", v=v, error="Invalid color code")
	v.verifiedcolor = verifiedcolor
	g.db.add(v)
	g.db.commit()
	return redirect("/settings/profile")

@app.post("/settings/security")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def settings_security_post(v):
	if request.values.get("new_password"):
		if request.values.get("new_password") != request.values.get("cnf_password"):
			return render_template("settings_security.html", v=v, error="Passwords do not match.")

		if not valid_password_regex.fullmatch(request.values.get("new_password")):
			return render_template("settings_security.html", v=v, error="Password must be between 8 and 100 characters.")

		if not v.verifyPass(request.values.get("old_password")):
			return render_template("settings_security.html", v=v, error="Incorrect password")

		v.passhash = v.hash_password(request.values.get("new_password"))
		v.sign_out_everywhere()
		session["login_nonce"] = v.login_nonce

		g.db.add(v)

		g.db.commit()

		return render_template("settings_security.html", v=v, msg="Your password has been changed.")

	if request.values.get("new_email"):

		if not v.verifyPass(request.values.get('password')):
			return render_template("settings_security.html", v=v, error="Invalid password.")

		new_email = request.values.get("new_email","").strip().lower()

		if not email_regex.fullmatch(new_email):
			return render_template("settings_security.html", v=v, error="Invalid email.")

		if new_email == v.email:
			return render_template("settings_security.html", v=v, error="That email is already yours!")

		link = activation_link(v, new_email)

		send_mail(to_address=new_email,
				  subject="Verify your email address.",
				  html=render_template("email/email_change.html",
									   action_url=link,
									   v=v)
				  )

		return render_template("settings_security.html", v=v, msg="Check your email and click the verification link to complete the email change.")

	if request.values.get("2fa_token"):
		if not v.verifyPass(request.values.get('password')):
			return render_template("settings_security.html", v=v, error="Invalid password or token.")

		if v.mfa_secret:
			return render_template("settings_security.html", v=v, error="Two-factor authentication is already enabled; disable it first.")

		secret = request.values.get("2fa_secret", "")
		try:
			valid = bool(secret) and pyotp.TOTP(secret).verify(request.values.get("2fa_token").strip(), valid_window=1)
		except ValueError: # not base32
			valid = False
		if not valid:
			return render_template("settings_security.html", v=v, error="Invalid password or token.")

		v.mfa_secret = secret
		g.db.add(v)

		g.db.commit()

		return render_template("settings_security.html", v=v, msg="Two-factor authentication enabled.")

	if request.values.get("2fa_remove"):

		if not v.verifyPass(request.values.get('password')):
			return render_template("settings_security.html", v=v, error="Invalid password or token.")

		token = request.values.get("2fa_remove")

		if not v.validate_2fa(token):
			return render_template("settings_security.html", v=v, error="Invalid password or token.")

		v.mfa_secret = None
		g.db.add(v)

		g.db.commit()

		return render_template("settings_security.html", v=v, msg="Two-factor authentication disabled.")

	abort(400)

@app.post("/settings/log_out_all_others")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def settings_log_out_others(v):
	submitted_password = request.values.get("password", "")

	if not v.verifyPass(submitted_password):
		return render_template("settings_security.html", v=v, error="Incorrect Password"), 401

	v.sign_out_everywhere()

	session["login_nonce"] = v.login_nonce

	g.db.add(v)

	g.db.commit()

	return render_template("settings_security.html", v=v, msg="All other devices have been logged out")


@app.post("/settings/images/profile")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def settings_images_profile(v):
	refuse_while_suspended(v)
	if request.headers.get("cf-ipcountry") == "T1": abort(403, "Image uploads are not allowed through TOR.")

	file = request.files["profile"]

	name = new_image_path()
	file.save(name)
	highres = process_image(name)

	name2 = name.replace('.webp', 'r.webp')
	copyfile(name, name2)
	imageurl = process_image(name2, resize=100)

	delete_uploaded_image(v.highres)
	delete_uploaded_image(v.profileurl)
	v.highres = highres
	v.profileurl = imageurl
	g.db.add(v)

	g.db.commit()

	return render_template("settings_profile.html", v=v, msg="Profile picture successfully updated.")


@app.post("/settings/images/banner")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def settings_images_banner(v):
	refuse_while_suspended(v)
	if request.headers.get("cf-ipcountry") == "T1": abort(403, "Image uploads are not allowed through TOR.")

	file = request.files["banner"]

	name = new_image_path()
	file.save(name)
	bannerurl = process_image(name)

	delete_uploaded_image(v.bannerurl)
	v.bannerurl = bannerurl
	g.db.add(v)
	g.db.commit()

	return render_template("settings_profile.html", v=v, msg="Banner successfully updated.")


@app.get("/settings/blocks")
@auth_required
def settings_blockedpage(v):
	return render_template("settings_blocks.html", v=v)

@app.get("/settings/css")
@auth_required
def settings_css_get(v):
	return render_template("settings_css.html", v=v)

@app.post("/settings/css")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def settings_css(v):
	css = sanitize_raw(request.values.get("css", "").replace('\\', ''), allow_newlines=True, length_limit=CSS_LENGTH_MAXIMUM)
	ok, err = validate_css(css)
	if not ok:
		abort(400, err)
	v.css = css
	g.db.add(v)
	g.db.commit()

	return render_template("settings_css.html", v=v)

@app.get("/settings/profilecss")
@auth_required
def settings_profilecss_get(v):
	return render_template("settings_profilecss.html", v=v)

@app.post("/settings/profilecss")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def settings_profilecss(v):
	refuse_while_suspended(v)
	profilecss = sanitize_raw(request.values.get("profilecss", "").replace('\\', ''), allow_newlines=True, length_limit=CSS_LENGTH_MAXIMUM)
	ok, err = validate_css(profilecss)
	if not ok:
		abort(400, err)
	v.profilecss = profilecss
	g.db.add(v)
	g.db.commit()
	return render_template("settings_profilecss.html", v=v)

@app.post("/settings/block")
@limiter.limit("1/second;10/day")
@auth_required
def settings_block_user(v):
	user = get_user(request.values.get("username"), graceful=True)

	if not user: abort(404, "That user doesn't exist.")

	if user.id == v.id:
		abort(409, "You can't block yourself.")

	if v.is_blocking(user):
		abort(409, f"You have already blocked @{user.username}.")

	if user.id == NOTIFICATIONS_ID:
		abort(409, "You can't block this user.")

	new_block = UserBlock(user_id=v.id,
						  target_id=user.id,
						  )
	g.db.add(new_block)
	g.db.commit()

	return {"message": f"@{user.username} blocked."}


@app.post("/settings/unblock")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def settings_unblock_user(v):
	user = get_user(request.values.get("username"))
	x = v.is_blocking(user)
	if not x: abort(409)
	g.db.delete(x)
	g.db.commit()

	return {"message": f"@{user.username} unblocked."}


@app.get("/settings/apps")
@auth_required
def settings_apps(v):
	refuse_api_client(v)
	tokens = {authorization.oauth_client: authorization.access_token for authorization in v.authorizations}
	return render_template("settings_apps.html", v=v, tokens=tokens)

@app.get("/settings/content")
@auth_required
def settings_content_get(v):
	return render_template("settings_filters.html", v=v)

@app.post("/settings/name_change")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@is_not_permabanned
def settings_name_change(v):
	refuse_while_suspended(v)
	new_name=request.values["name"].strip()

	if new_name==v.username:
		return render_template("settings_profile.html",
						   v=v,
						   error="You didn't change anything")

	if not valid_username_regex.fullmatch(new_name):
		return render_template("settings_profile.html",
						   v=v,
						   error="This isn't a valid username.")

	x = g.db.query(User).filter(
		or_(
			func.lower(User.username) == new_name.lower(),
			func.lower(User.original_username) == new_name.lower()
			)
		).one_or_none()

	if x and x.id != v.id:
		return render_template("settings_profile.html",
						   v=v,
						   error=f"Username `{new_name}` is already in use.")

	v=g.db.query(User).filter_by(id=v.id).one_or_none()

	v.username=new_name
	g.db.add(v)
	g.db.commit()

	return redirect("/settings/profile")

@app.post("/settings/title_change")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def settings_title_change(v):
	refuse_while_suspended(v)
	if v.flairchanged: abort(403)
	
	new_name=request.values["title"].strip()[:100].replace("𒐪","")

	if new_name==v.customtitleplain: return render_template("settings_profile.html", v=v, error="You didn't change anything")

	v.customtitleplain = new_name

	v.customtitle = filter_emojis_only(new_name)

	g.db.add(v)
	g.db.commit()

	return redirect("/settings/profile")


@app.get("/settings")
@auth_required
def settings(v):
	return redirect("/settings/profile")


@app.get("/settings/profile")
@auth_required
def settings_profile(v):
	if v.flairchanged: ti = datetime.utcfromtimestamp(v.flairchanged).strftime('%Y-%m-%d %H:%M:%S')
	else: ti = ''
	return render_template("settings_profile.html", v=v, ti=ti)


# other settings i guess

@app.post("/id/<int:id>/private/<int:enabled>")
@auth_required
def post_set_user_profile_privacy(v: User, id: int, enabled: int):
	if enabled != 0 and enabled != 1: abort(400, "'enabled' must be '0' or '1'")
	user: User = get_account(id)
	if not user.can_change_user_privacy(v): abort(403)
	user.is_private = bool(enabled)
	g.db.commit()
	return {"message": f"{'Enabled' if user.is_private else 'Disabled'} private mode successfully!"}
