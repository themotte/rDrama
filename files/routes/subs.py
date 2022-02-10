from files.__main__ import app, limiter, mail
from files.helpers.alerts import *
from files.helpers.wrappers import *
from files.classes import *
from .front import frontlist

valid_sub_regex = re.compile("^[a-zA-Z0-9_\-]{3,25}$")

@app.get("/s/<sub>/mods")
@auth_required
def mods(v, sub):
	sub = g.db.query(Sub).filter_by(name=sub.lower()).one_or_none()
	if not sub: abort(404)

	mods = [x[0] for x in g.db.query(Mod.user_id).filter_by(sub=sub.name).all()]
	users = g.db.query(User).filter(User.id.in_(mods)).all()
	return render_template("sub/mods.html", v=v, sub=sub, users=users)


@app.post("/s/<sub>/add_mod")
@auth_required
def add_mod(v, sub):
	sub = g.db.query(Sub).filter_by(name=sub.lower()).one_or_none()
	if not sub: abort(404)
	sub = sub.name

	if not v.mods(sub): abort(403)

	user = request.values.get('user')

	if not user: abort(400)

	user = get_user(user)

	mod = Mod(user_id=user.id, sub=sub)
	g.db.add(mod)

	send_repeatable_notification(user.id, f"You have been added as a mod to /s/{sub}")

	g.db.commit()
	
	return redirect(f'/s/{sub}/mods')


@app.get("/create_sub")
@auth_required
def create_sub(v):
	return render_template("sub/create_sub.html", v=v)


@app.post("/create_sub")
@auth_required
def create_sub2(v):
	name = request.values.get('name')
	if not name: abort(400)
	name = name.strip().lower()

	if not re.fullmatch(valid_sub_regex, name):
		return render_template("sub/create_sub.html", v=v, error="Sub name not allowed."), 400

	sub = g.db.query(Sub).filter_by(name=name).one_or_none()
	if not sub:
		cost = v.subs_created * 25
		if v.coins < cost:
			return render_template("sub/create_sub.html", v=v, error="You don't have enough coins!"), 403

		v.coins -= cost
		v.subs_created += 1
		g.db.add(v)

		sub = Sub(name=name)
		g.db.add(sub)
		mod = Mod(user_id=v.id, sub=sub.name)
		g.db.add(mod)
		g.db.commit()

	return redirect(f'/s/{sub.name}')

@app.post("/kick/<pid>")
@auth_required
def kick(v, pid):
	try: pid = int(pid)
	except: abort(400)

	post = get_post(pid)

	if not post.sub: abort(403)
	if not v.mods(post.sub): abort(403)

	post.sub = 'general'
	g.db.add(post)
	g.db.commit()

	cache.delete_memoized(frontlist)

	return {"message": "Post kicked successfully!"}


@app.get('/s/<sub>/settings')
@auth_required
def sub_settings(v, sub):
	sub = g.db.query(Sub).filter_by(name=sub.strip().lower()).one_or_none()
	if not sub: abort(404)

	if not v.mods(sub.name): abort(403)

	return render_template('sub/settings.html', v=v, sidebar=sub.sidebar, sub=sub)


@app.post('/s/<sub>/sidebar')
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def post_sub_sidebar(v, sub):
	sub = g.db.query(Sub).filter_by(name=sub.lower()).one_or_none()
	if not sub: abort(404)
	
	if not v.mods(sub.name): abort(403)

	sub.sidebar = request.values.get('sidebar', '').strip()
	sub.sidebar_html = sanitize(sub.sidebar)
	g.db.add(sub)

	ma = ModAction(
		kind="change_sidebar",
		user_id=v.id
	)
	g.db.add(ma)

	g.db.commit()

	return redirect(f'/s/{sub.name}/settings')


@app.post("/s/<sub>/banner")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def sub_banner(v, sub):
	if v and v.patron:
		if request.content_length > 8 * 1024 * 1024: return {"error":"Max file size is 8 MB."}, 413
	elif request.content_length > 4 * 1024 * 1024: return {"error":"Max file size is 4 MB."}, 413

	if request.headers.get("cf-ipcountry") == "T1": return {"error":"Image uploads are not allowed through TOR."}, 403

	sub = g.db.query(Sub).filter_by(name=sub.lower().strip()).one_or_none()
	if not sub: abort(404)

	if not v.mods(sub.name): abort(403)

	file = request.files["banner"]

	name = f'/images/{time.time()}'.replace('.','')[:-5] + '.webp'
	file.save(name)
	bannerurl = process_image(name)

	if bannerurl:
		if sub.bannerurl and '/images/' in sub.bannerurl:
			fpath = '/images/' + sub.bannerurl.split('/images/')[1]
			if path.isfile(fpath): os.remove(fpath)
		sub.bannerurl = bannerurl
		g.db.add(sub)
		g.db.commit()

	return redirect(f'/s/{sub.name}/settings')

@app.post("/s/<sub>/sidebar_image")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def sub_sidebar(v, sub):
	if v and v.patron:
		if request.content_length > 8 * 1024 * 1024: return {"error":"Max file size is 8 MB."}, 413
	elif request.content_length > 4 * 1024 * 1024: return {"error":"Max file size is 4 MB."}, 413

	if request.headers.get("cf-ipcountry") == "T1": return {"error":"Image uploads are not allowed through TOR."}, 403

	sub = g.db.query(Sub).filter_by(name=sub.lower().strip()).one_or_none()
	if not sub: abort(404)

	if not v.mods(sub.name): abort(403)
	
	file = request.files["sidebar"]
	name = f'/images/{time.time()}'.replace('.','')[:-5] + '.webp'
	file.save(name)
	sidebarurl = process_image(name)

	if sidebarurl:
		if sub.sidebarurl and '/images/' in sub.sidebarurl:
			fpath = '/images/' + sub.sidebarurl.split('/images/')[1]
			if path.isfile(fpath): os.remove(fpath)
		sub.sidebarurl = sidebarurl
		g.db.add(sub)
		g.db.commit()

	return redirect(f'/s/{sub.name}/settings')


#create general
#subs urls
#-----
#mods id seq
#css
#exile
#guild mod log
#remove mod
#search sub