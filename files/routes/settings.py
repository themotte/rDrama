import os

from files.__main__ import app, cache, limiter
from files.helpers.alerts import *
from files.helpers.const import *
from files.helpers.media import process_image
from files.helpers.sanitize import *
from files.helpers.sanitize import filter_emojis_only
from files.helpers.security import generate_hash
from files.helpers.wrappers import auth_required, is_not_permabanned
from files.mail import send_mail
from files.routes.importstar import *

from .front import frontlist

tiers={
	"(Paypig)": 1,
	"(Renthog)": 2,
	"(Landchad)": 3,
	"(Terminally online turboautist)": 4,
	"(Marsey's Sugar Daddy)": 5,
	"(JIDF Bankroller)": 6,
	"(Rich Bich)": 7,
	"(LlamaBean)": 1,
	}

@app.post("/settings/removebackground")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def removebackground(v):
	v.background = None
	g.db.add(v)
	g.db.commit()
	return {"message": "Background removed!"}

@app.post("/settings/profile")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def settings_profile_post(v):
	updated = False

	if request.values.get("background", v.background) != v.background:
		updated = True
		v.background = request.values.get("background")

	elif request.values.get("reddit", v.reddit) != v.reddit:
		reddit = request.values.get("reddit")
		if reddit in {'old.reddit.com', 'reddit.com', 'i.reddit.com', 'teddit.net', 'libredd.it', 'unddit.com'}:
			updated = True
			v.reddit = reddit

	elif request.values.get("hidevotedon", v.hidevotedon) != v.hidevotedon:
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

	elif request.values.get("nitter", v.nitter) != v.nitter:
		updated = True
		v.nitter = request.values.get("nitter") == 'true'

	elif request.values.get("controversial", v.controversial) != v.controversial:
		updated = True
		v.controversial = request.values.get("controversial") == 'true'

	elif request.values.get("over18", v.over_18) != v.over_18:
		updated = True
		v.over_18 = request.values.get("over18") == 'true'
		
	elif request.values.get("private", v.is_private) != v.is_private:
		updated = True
		v.is_private = request.values.get("private") == 'true'

	elif request.values.get("nofollow", v.is_nofollow) != v.is_nofollow:
		updated = True
		v.is_nofollow = request.values.get("nofollow") == 'true'

	elif request.values.get("bio") == "":
		v.bio = None
		v.bio_html = None
		g.db.add(v)
		g.db.commit()
		return render_template("settings_profile.html", v=v, msg="Your bio has been updated.")

	elif request.values.get("friends") == "":
		v.friends = None
		v.friends_html = None
		g.db.add(v)
		g.db.commit()
		return render_template("settings_profile.html", v=v, msg="Your friends list has been updated.")

	elif request.values.get("enemies") == "":
		v.enemies = None
		v.enemies_html = None
		g.db.add(v)
		g.db.commit()
		return render_template("settings_profile.html", v=v, msg="Your enemies list has been updated.")

	elif request.values.get("friends"):
		friends = request.values.get("friends")[:500]

		friends_html = sanitize(friends)

		if len(friends_html) > 2000:
			return render_template("settings_profile.html",
								   v=v,
								   error="Your friends list is too long")


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


	elif request.values.get("enemies"):
		enemies = request.values.get("enemies")[:500]

		enemies_html = sanitize(enemies)

		if len(enemies_html) > 2000:
			return render_template("settings_profile.html",
								   v=v,
								   error="Your enemies list is too long")


		notify_users = NOTIFY_USERS(enemies, v)

		if notify_users:
			cid = notif_comment(f"@{v.username} has added you to their enemies list!")
			for x in notify_users:
				add_notif(cid, x)

		v.enemies = enemies[:500]
		v.enemies_html=enemies_html
		g.db.add(v)
		g.db.commit()
		return render_template("settings_profile.html",
							   v=v,
							   msg="Your enemies list has been updated.")


	elif request.values.get("bio") or request.files.get('file') and request.headers.get("cf-ipcountry") != "T1":
		bio = request.values.get("bio")[:1500]

		if request.files.get('file'):
			file = request.files['file']
			if file.content_type.startswith('image/'):
				name = f'/images/{time.time()}'.replace('.','') + '.webp'
				file.save(name)
				url = process_image(name)
				bio += f"\n\n![]({url})"
			else:
				if request.headers.get("Authorization") or request.headers.get("xhr"): abort(400, "Image files only")
				return render_template("settings_profile.html", v=v, error="Image files only"), 400
		
		bio_html = sanitize(bio)

		if len(bio_html) > 10000:
			return render_template("settings_profile.html",
								   v=v,
								   error="Your bio is too long")

		if len(bio_html) > 10000: abort(400)

		v.bio = bio[:1500]
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
			cache.delete_memoized(frontlist)
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

	defaulttime = request.values.get("defaulttime")
	if defaulttime:
		if defaulttime in {"hour", "day", "week", "month", "year", "all"}:
			v.defaulttime = defaulttime
			updated = True
		else: abort(400)

	theme = request.values.get("theme")
	if theme:
		if theme in THEMES:
			if theme == "transparent" and not v.background: 
				abort(400, "You need to set a background to use the transparent theme!")
			v.theme = theme
			if theme == "win98": v.themecolor = "30409f"
			updated = True
		else: abort(400)

	house = request.values.get("house")
	if house and house in ("None","Furry","Femboy","Vampire","Racist"):
		if v.house: cost = 2000
		else: cost = 500

		if v.coins >= cost: v.coins -= cost
		elif v.procoins >= cost: v.procoins -= cost
		else: abort(403)

		if house == "None": house = None 
		v.house = house
		updated = True

	if updated:
		g.db.add(v)
		g.db.commit()

		return {"message": "Your settings have been updated."}

	else:
		abort(400, "You didn't change anything.")


@app.post("/settings/filters")
@auth_required
def filters(v):
	filters=request.values.get("filters")[:1000].strip()

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

	cache.delete_memoized(frontlist)

	g.db.commit()
	if v.changelogsub: return {"message": "You have subscribed to the changelog!"}
	else: return {"message": "You have unsubscribed from the changelog!"}

@app.post("/settings/namecolor")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def namecolor(v):

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

		g.db.add(v)

		g.db.commit()

		return render_template("settings_security.html", v=v, msg="Your password has been changed.")

	if request.values.get("new_email"):

		if not v.verifyPass(request.values.get('password')):
			return render_template("settings_security.html", v=v, error="Invalid password.")

		new_email = request.values.get("new_email","").strip().lower()

		if new_email == v.email:
			return render_template("settings_security.html", v=v, error="That email is already yours!")

		url = f"{SITE_FULL}/activate"

		now = int(time.time())

		token = generate_hash(f"{new_email}+{v.id}+{now}")
		params = f"?email={quote(new_email)}&id={v.id}&time={now}&token={token}"

		link = url + params

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

		secret = request.values.get("2fa_secret")
		x = pyotp.TOTP(secret)
		if not x.verify(request.values.get("2fa_token"), valid_window=1):
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

@app.post("/settings/log_out_all_others")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def settings_log_out_others(v):

	submitted_password = request.values.get("password", "").strip()

	if not v.verifyPass(submitted_password):
		return render_template("settings_security.html", v=v, error="Incorrect Password"), 401

	v.login_nonce += 1

	session["login_nonce"] = v.login_nonce

	g.db.add(v)

	g.db.commit()

	return render_template("settings_security.html", v=v, msg="All other devices have been logged out")


@app.post("/settings/images/profile")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def settings_images_profile(v):
	if request.headers.get("cf-ipcountry") == "T1": abort(403, "Image uploads are not allowed through TOR.")

	file = request.files["profile"]

	name = f'/images/{time.time()}'.replace('.','') + '.webp'
	file.save(name)
	highres = process_image(name)

	if not highres: abort(400)

	name2 = name.replace('.webp', 'r.webp')
	copyfile(name, name2)
	imageurl = process_image(name2, resize=100)

	if not imageurl: abort(400)

	if v.highres and '/images/' in v.highres:
		fpath = '/images/' + v.highres.split('/images/')[1]
		if path.isfile(fpath): os.remove(fpath)
	if v.profileurl and '/images/' in v.profileurl:
		fpath = '/images/' + v.profileurl.split('/images/')[1]
		if path.isfile(fpath): os.remove(fpath)
	v.highres = highres
	v.profileurl = imageurl
	g.db.add(v)

	g.db.commit()

	return render_template("settings_profile.html", v=v, msg="Profile picture successfully updated.")


@app.post("/settings/images/banner")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def settings_images_banner(v):
	if request.headers.get("cf-ipcountry") == "T1": abort(403, "Image uploads are not allowed through TOR.")

	file = request.files["banner"]

	name = f'/images/{time.time()}'.replace('.','') + '.webp'
	file.save(name)
	bannerurl = process_image(name)

	if bannerurl:
		if v.bannerurl and '/images/' in v.bannerurl:
			fpath = '/images/' + v.bannerurl.split('/images/')[1]
			if path.isfile(fpath): os.remove(fpath)
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
	cache.delete_memoized(frontlist)
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
	cache.delete_memoized(frontlist)
	g.db.commit()

	return {"message": f"@{user.username} unblocked."}


@app.get("/settings/apps")
@auth_required
def settings_apps(v):
	return render_template("settings_apps.html", v=v)

@app.get("/settings/content")
@auth_required
def settings_content_get(v):
	return render_template("settings_filters.html", v=v)

@app.post("/settings/name_change")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@is_not_permabanned
def settings_name_change(v):

	new_name=request.values.get("name").strip()

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
	v.name_changed_utc=int(time.time())
	g.db.add(v)
	g.db.commit()

	return redirect("/settings/profile")

@app.post("/settings/title_change")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def settings_title_change(v):

	if v.flairchanged: abort(403)
	
	new_name=request.values.get("title").strip()[:100].replace("𒐪","")

	if new_name==v.customtitle: return render_template("settings_profile.html", v=v, error="You didn't change anything")

	v.customtitleplain = new_name

	v.customtitle = filter_emojis_only(new_name)

	if len(v.customtitle) < 1000:
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
