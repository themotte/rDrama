from drama.helpers.wrappers import *
from drama.helpers.alerts import *
from drama.helpers.get import *
from drama.classes import *
from flask import *
from drama.__main__ import app

@app.get("/authorize")
@auth_required
def authorize_prompt(v):
	client_id = request.args.get("client_id")
	application = g.db.query(OauthApp).filter_by(client_id=client_id).first()

	if not application: return {"oauth_error": "Invalid `client_id`"}, 401
	if application.is_banned: return {"oauth_error": f"Application `{application.app_name}` is suspended."}, 403
	redirect_uri = request.args.get("redirect_uri")
	if not redirect_uri: return {"oauth_error": f"`redirect_uri` must be provided."}, 400
	return render_template("oauth.html", v=v, application=application, redirect_uri=redirect_uri)


@app.post("/authorize")
@auth_required
@validate_formkey
def oauth(v):

	client_id = request.form.get("client_id")
	application = g.db.query(OauthApp).filter_by(client_id=client_id).first()
	if not application: return {"oauth_error": "Invalid `client_id`"}, 401
	if application.is_banned: return {"oauth_error": f"Application `{application.app_name}` is suspended."}, 403
	access_token = secrets.token_urlsafe(128)[:128]
	new_auth = ClientAuth(
		oauth_client = application.id,
		user_id = v.id,
		access_token=access_token
	)

	g.db.add(new_auth)

	return redirect(f"{application.redirect_uri}?token={access_token}")


@app.post("/api_keys")
@is_not_banned
def request_api_keys(v):

	new_app = OauthApp(
		app_name=request.form.get('name'),
		redirect_uri=request.form.get('redirect_uri'),
		author_id=v.id,
		description=request.form.get("description")[:256]
	)

	g.db.add(new_app)

	send_admin(1046, f"@{v.username} has requested API keys for `{request.form.get('name')}`. You can approve or deny the request [here](/admin/apps).")

	return redirect('/settings/apps')


@app.post("/delete_app/<aid>")
@is_not_banned
@validate_formkey
def delete_oauth_app(v, aid):

	aid = int(aid)
	app = g.db.query(OauthApp).filter_by(id=aid).first()

	for auth in g.db.query(ClientAuth).filter_by(oauth_client=app.id).all():
		g.db.delete(auth)

	g.db.commit()

	g.db.delete(app)

	return redirect('/apps')


@app.post("/edit_app/<aid>")
@is_not_banned
@validate_formkey
def edit_oauth_app(v, aid):

	aid = int(aid)
	app = g.db.query(OauthApp).filter_by(id=aid).first()

	app.redirect_uri = request.form.get('redirect_uri')
	app.app_name = request.form.get('name')
	app.description = request.form.get("description")[:256]

	g.db.add(app)

	return redirect('/settings/apps')


@app.route("/identity")
@auth_required
def api_v1_identity(v):
	return v.json


@app.post("/admin/app/approve/<aid>")
@admin_level_required(3)
@validate_formkey
def admin_app_approve(v, aid):

	app = g.db.query(OauthApp).filter_by(id=aid).first()

	app.client_id = secrets.token_urlsafe(64)[:64]
	app.client_secret = secrets.token_urlsafe(128)[:128]

	g.db.add(app)

	u = get_account(app.author_id, v=v)
	send_notification(1046, u, f"Your application `{app.app_name}` has been approved.")

	return {"message": f"{app.app_name} approved"}


@app.post("/admin/app/revoke/<aid>")
@admin_level_required(3)
@validate_formkey
def admin_app_revoke(v, aid):

	app = g.db.query(OauthApp).filter_by(id=aid).first()

	app.client_id = None
	app.client_secret = None

	g.db.add(app)

	u = get_account(app.author_id, v=v)
	send_notification(1046, u, f"Your application `{app.app_name}` has been revoked.")

	return {"message": f"{app.app_name} revoked"}


@app.post("/admin/app/reject/<aid>")
@admin_level_required(3)
@validate_formkey
def admin_app_reject(v, aid):

	app = g.db.query(OauthApp).filter_by(id=aid).first()

	for auth in g.db.query(ClientAuth).filter_by(oauth_client=app.id).all():
		g.db.delete(auth)

	g.db.flush()
	u = get_account(app.author_id, v=v)
	send_notification(1046, u, f"Your application `{app.app_name}` has been rejected.")

	g.db.delete(app)

	return {"message": f"{app.app_name} rejected"}


@app.get("/admin/app/<aid>")
@admin_level_required(3)
def admin_app_id(v, aid):

	aid=aid

	oauth = g.db.query(OauthApp).options(
		joinedload(
			OauthApp.author)).filter_by(
		id=aid).first()

	pids=oauth.idlist(page=int(request.args.get("page",1)),
		)

	next_exists=len(pids)==101
	pids=pids[:100]

	posts=get_posts(pids, v=v)

	return render_template("admin/app.html",
						   v=v,
						   app=oauth,
						   listing=posts,
						   next_exists=next_exists
						   )

@app.get("/admin/app/<aid>/comments")
@admin_level_required(3)
def admin_app_id_comments(v, aid):

	aid=aid

	oauth = g.db.query(OauthApp).options(
		joinedload(
			OauthApp.author)).filter_by(
		id=aid).first()

	cids=oauth.comments_idlist(page=int(request.args.get("page",1)),
		)

	next_exists=len(cids)==101
	cids=cids[:100]

	comments=get_comments(cids, v=v)


	return render_template("admin/app.html",
						   v=v,
						   app=oauth,
						   comments=comments,
						   next_exists=next_exists,
						   standalone=True
						   )


@app.get("/admin/apps")
@admin_level_required(3)
def admin_apps_list(v):

	apps = g.db.query(OauthApp).options(
		joinedload(
			OauthApp.author)).filter(
		OauthApp.client_id==None).order_by(
				OauthApp.id.desc()).all()

	return render_template("admin/apps.html", v=v, apps=apps)


@app.post("/oauth/reroll/<aid>")
@auth_required
def reroll_oauth_tokens(aid, v):

	aid = aid

	a = g.db.query(OauthApp).filter_by(id=aid).first()

	if a.author_id != v.id:
		abort(403)

	a.client_id = secrets.token_urlsafe(64)[:64]
	a.client_secret = secrets.token_urlsafe(128)[:128]

	g.db.add(a)

	return {"message": "Tokens Rerolled", "id": a.client_id, "secret": a.client_secret}


@app.post("/oauth/rescind/<aid>")
@auth_required
@validate_formkey
def oauth_rescind_app(aid, v):

	aid = aid
	auth = g.db.query(ClientAuth).filter_by(id=aid).first()

	if auth.user_id != v.id:
		abort(403)

	g.db.delete(auth)

	return {"message": f"{auth.application.app_name} Revoked"}

@app.post("/release")
@auth_required
def oauth_release_auth(v):

	token=request.headers.get("Authorization").split()[1]

	auth = g.db.query(ClientAuth).filter_by(user_id=v.id, access_token=token).first()
	if not auth:
		abort(404)

	if not auth.refresh_token:
		abort(400)

	auth.access_token_expire_utc=0
	g.db.add(auth)

	return {"message":"Authorization released"}

@app.post("/kill")
@auth_required
def oauth_kill_auth(v):

	token=request.headers.get("Authorization").split()[1]

	auth = g.db.query(ClientAuth).filter_by(user_id=v.id, access_token=token).first()
	if not auth:
		abort(404)

	g.db.delete(auth)

	return {"message":"Authorization released"}
