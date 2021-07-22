from drama.helpers.wrappers import *
from drama.helpers.alerts import *
from drama.helpers.get import *
from drama.classes import *
from flask import *
from drama.__main__ import app

SCOPES = {
	'identity': 'See your username',
	'create': 'Save posts and comments as you',
	'read': 'View Drama as you, including private or restricted content',
	'update': 'Edit your posts and comments',
	'delete': 'Delete your posts and comments',
	'vote': 'Cast votes as you',
	'guildmaster': 'Perform Badmin actions'
}


@app.route("/oauth/authorize", methods=["GET"])
@auth_required
def oauth_authorize_prompt(v):
	'''
	This page takes the following URL parameters:
	* client_id - Your application client ID
	* scope - Comma-separated list of scopes. Scopes are described above
	* redirect_uri - Your redirect link
	* state - Your anti-csrf token
	'''

	client_id = request.args.get("client_id")

	application = get_application(client_id)
	if not application:
		return jsonify({"oauth_error": "Invalid `client_id`"}), 401

	if application.is_banned:
		return jsonify({"oauth_error": f"Application `{application.app_name}` is suspended."}), 403

	scopes_txt = request.args.get('scope', "")

	scopes = scopes_txt.split(',')
	if not scopes:
		return jsonify(
			{"oauth_error": "One or more scopes must be specified as a comma-separated list."}), 400

	for scope in scopes:
		if scope not in SCOPES:
			return jsonify({"oauth_error": f"The provided scope `{scope}` is not valid."}), 400

	if any(x in scopes for x in ["create", "update",
								 "guildmaster"]) and "identity" not in scopes:
		return jsonify({"oauth_error": f"`identity` scope required when requesting `create`, `update`, or `guildmaster` scope."}), 400

	redirect_uri = request.args.get("redirect_uri")
	if not redirect_uri:
		return jsonify({"oauth_error": f"`redirect_uri` must be provided."}), 400

	valid_redirect_uris = [x.strip()
						   for x in application.redirect_uri.split(",")]

	if redirect_uri not in valid_redirect_uris:
		return jsonify({"oauth_error": "Invalid redirect_uri"}), 400

	state = request.args.get("state")
	if not state:
		return jsonify({'oauth_error': 'state argument required'}), 400

	permanent = bool(request.args.get("permanent"))

	return render_template("oauth.html",
						   v=v,
						   application=application,
						   SCOPES=SCOPES,
						   state=state,
						   scopes=scopes,
						   scopes_txt=scopes_txt,
						   redirect_uri=redirect_uri,
						   permanent=int(permanent),
						   i=random_image()
						   )


@app.route("/oauth/authorize", methods=["POST"])
@auth_required
@validate_formkey
def oauth_authorize_post(v):

	client_id = request.form.get("client_id")
	scopes_txt = request.form.get("scopes")
	state = request.form.get("state")
	redirect_uri = request.form.get("redirect_uri")

	application = get_application(client_id)
	if not application:
		return jsonify({"oauth_error": "Invalid `client_id`"}), 401
	if application.is_banned:
		return jsonify({"oauth_error": f"Application `{application.app_name}` is suspended."}), 403

	valid_redirect_uris = [x.strip()
						   for x in application.redirect_uri.split(",")]
	if redirect_uri not in valid_redirect_uris:
		return jsonify({"oauth_error": "Invalid redirect_uri"}), 400

	scopes = scopes_txt.split(',')
	if not scopes:
		return jsonify(
			{"oauth_error": "One or more scopes must be specified as a comma-separated list"}), 400

	for scope in scopes:
		if scope not in SCOPES:
			return jsonify({"oauth_error": f"The provided scope `{scope}` is not valid."}), 400

	if any(x in scopes for x in ["create", "update",
								 "guildmaster"]) and "identity" not in scopes:
		return jsonify({"oauth_error": f"`identity` scope required when requesting `create`, `update`, or `guildmaster` scope."}), 400

	if not state:
		return jsonify({'oauth_error': 'state argument required'}), 400

	permanent = bool(int(request.values.get("permanent", 0)))

	new_auth = ClientAuth(
		oauth_client=application.id,
		oauth_code=secrets.token_urlsafe(128)[0:128],
		user_id=v.id,
		scope_identity="identity" in scopes,
		scope_create="create" in scopes,
		scope_read="read" in scopes,
		scope_update="update" in scopes,
		scope_delete="delete" in scopes,
		scope_vote="vote" in scopes,
		scope_guildmaster="guildmaster" in scopes,
		refresh_token=secrets.token_urlsafe(128)[0:128] if permanent else None
	)

	g.db.add(new_auth)

	return redirect(f"{redirect_uri}?code={new_auth.oauth_code}&scopes={scopes_txt}&state={state}")


@app.route("/oauth/grant", methods=["POST"])
def oauth_grant():
	'''
	This endpoint takes the following parameters:
	* code - The code parameter provided in the redirect
	* client_id - Your client ID
	* client_secret - your client secret
	'''

	application = g.db.query(OauthApp).filter_by(
		client_id=request.values.get("client_id"),
		client_secret=request.values.get("client_secret")).first()
	if not application:
		return jsonify(
			{"oauth_error": "Invalid `client_id` or `client_secret`"}), 401
	if application.is_banned:
		return jsonify({"oauth_error": f"Application `{application.app_name}` is suspended."}), 403

	if request.values.get("grant_type") == "code":

		code = request.values.get("code")
		if not code:
			return jsonify({"oauth_error": "code required"}), 400

		auth = g.db.query(ClientAuth).filter_by(
			oauth_code=code,
			access_token=None,
			oauth_client=application.id
		).first()

		if not auth:
			return jsonify({"oauth_error": "Invalid code"}), 401

		auth.oauth_code = None
		auth.access_token = secrets.token_urlsafe(128)[0:128]
		auth.access_token_expire_utc = int(time.time()) + 60 * 60

		g.db.add(auth)

		g.db.commit()

		data = {
			"access_token": auth.access_token,
			"scopes": auth.scopelist,
			"expires_at": auth.access_token_expire_utc,
			"token_type": "Bearer"
		}

		if auth.refresh_token:
			data["refresh_token"] = auth.refresh_token

		return jsonify(data)

	elif request.values.get("grant_type") == "refresh":

		refresh_token = request.values.get('refresh_token')
		if not refresh_token:
			return jsonify({"oauth_error": "refresh_token required"}), 401

		auth = g.db.query(ClientAuth).filter_by(
			refresh_token=refresh_token,
			oauth_code=None,
			oauth_client=application.id
		).first()

		if not auth:
			return jsonify({"oauth_error": "Invalid refresh_token"}), 401

		auth.access_token = secrets.token_urlsafe(128)[0:128]
		auth.access_token_expire_utc = int(time.time()) + 60 * 60

		g.db.add(auth)

		data = {
			"access_token": auth.access_token,
			"scopes": auth.scopelist,
			"expires_at": auth.access_token_expire_utc
		}

		return jsonify(data)

	else:
		return jsonify({"oauth_error": f"Invalid grant_type `{request.values.get('grant_type','')}`. Expected `code` or `refresh`."}), 400


@app.route("/api_keys", methods=["POST"])
@is_not_banned
def request_api_keys(v):

	new_app = OauthApp(
		app_name=request.form.get('name'),
		redirect_uri=request.form.get('redirect_uri'),
		author_id=v.id,
		description=request.form.get("description")[0:256]
	)

	g.db.add(new_app)

	send_admin(1046, f"@{v.username} has requested API keys for `{request.form.get('name')}`. You can approve or deny the request [here](/admin/apps).")

	return redirect('/settings/apps')


@app.route("/delete_app/<aid>", methods=["POST"])
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


@app.route("/edit_app/<aid>", methods=["POST"])
@is_not_banned
@validate_formkey
def edit_oauth_app(v, aid):

	aid = int(aid)
	app = g.db.query(OauthApp).filter_by(id=aid).first()

	app.redirect_uri = request.form.get('redirect_uri')
	app.app_name = request.form.get('name')
	app.description = request.form.get("description")[0:256]

	g.db.add(app)

	return redirect('/settings/apps')


@app.route("/api/v1/identity")
@auth_required
@api("identity")
def api_v1_identity(v):

	return jsonify(v.json)


@app.route("/admin/app/approve/<aid>", methods=["POST"])
@admin_level_required(3)
@validate_formkey
def admin_app_approve(v, aid):

	app = g.db.query(OauthApp).filter_by(id=base36decode(aid)).first()

	app.client_id = secrets.token_urlsafe(64)[0:64]
	app.client_secret = secrets.token_urlsafe(128)[0:128]

	g.db.add(app)

	u = get_account(app.author_id, v=v)
	send_notification(1046, u, f"Your application `{app.app_name}` has been approved.")

	return jsonify({"message": f"{app.app_name} approved"})


@app.route("/admin/app/revoke/<aid>", methods=["POST"])
@admin_level_required(3)
@validate_formkey
def admin_app_revoke(v, aid):

	app = g.db.query(OauthApp).filter_by(id=base36decode(aid)).first()

	app.client_id = None
	app.client_secret = None

	g.db.add(app)

	u = get_account(app.author_id, v=v)
	send_notification(1046, u, f"Your application `{app.app_name}` has been revoked.")

	return jsonify({"message": f"{app.app_name} revoked"})


@app.route("/admin/app/reject/<aid>", methods=["POST"])
@admin_level_required(3)
@validate_formkey
def admin_app_reject(v, aid):

	app = g.db.query(OauthApp).filter_by(id=base36decode(aid)).first()

	for auth in g.db.query(ClientAuth).filter_by(oauth_client=app.id).all():
		g.db.delete(auth)

	g.db.flush()
	u = get_account(app.author_id, v=v)
	send_notification(1046, u, f"Your application `{app.app_name}` has been rejected.")

	g.db.delete(app)

	return jsonify({"message": f"{app.app_name} rejected"})


@app.route("/admin/app/<aid>", methods=["GET"])
@admin_level_required(3)
def admin_app_id(v, aid):

	aid=base36decode(aid)

	oauth = g.db.query(OauthApp).options(
		joinedload(
			OauthApp.author)).filter_by(
		id=aid).first()

	pids=oauth.idlist(page=int(request.args.get("page",1)),
		)

	next_exists=len(pids)==101
	pids=pids[0:100]

	posts=get_posts(pids, v=v)

	return render_template("admin/app.html",
						   v=v,
						   app=oauth,
						   listing=posts,
						   next_exists=next_exists
						   )

@app.route("/admin/app/<aid>/comments", methods=["GET"])
@admin_level_required(3)
def admin_app_id_comments(v, aid):

	aid=base36decode(aid)

	oauth = g.db.query(OauthApp).options(
		joinedload(
			OauthApp.author)).filter_by(
		id=aid).first()

	cids=oauth.comments_idlist(page=int(request.args.get("page",1)),
		)

	next_exists=len(cids)==101
	cids=cids[0:100]

	comments=get_comments(cids, v=v)


	return render_template("admin/app.html",
						   v=v,
						   app=oauth,
						   comments=comments,
						   next_exists=next_exists,
						   standalone=True
						   )


@app.route("/admin/apps", methods=["GET"])
@admin_level_required(3)
def admin_apps_list(v):

	apps = g.db.query(OauthApp).options(
		joinedload(
			OauthApp.author)).filter(
		OauthApp.client_id==None).order_by(
				OauthApp.id.desc()).all()

	return render_template("admin/apps.html", v=v, apps=apps)


@app.route("/oauth/reroll/<aid>", methods=["POST"])
@auth_required
def reroll_oauth_tokens(aid, v):

	aid = base36decode(aid)

	a = g.db.query(OauthApp).filter_by(id=aid).first()

	if a.author_id != v.id:
		abort(403)

	a.client_id = secrets.token_urlsafe(64)[0:64]
	a.client_secret = secrets.token_urlsafe(128)[0:128]

	g.db.add(a)

	return jsonify({"message": "Tokens Rerolled",
					"id": a.client_id,
					"secret": a.client_secret
					}
				   )


@app.route("/oauth/rescind/<aid>", methods=["POST"])
@auth_required
@validate_formkey
def oauth_rescind_app(aid, v):

	aid = base36decode(aid)
	auth = g.db.query(ClientAuth).filter_by(id=aid).first()

	if auth.user_id != v.id:
		abort(403)

	g.db.delete(auth)

	return jsonify({"message": f"{auth.application.app_name} Revoked"})

@app.route("/api/v1/release", methods=["POST"])
@auth_required
@api()
def oauth_release_auth(v):

	token=request.headers.get("Authorization").split()[1]

	auth = g.db.query(ClientAuth).filter_by(user_id=v.id, access_token=token).first()
	if not auth:
		abort(404)

	if not auth.refresh_token:
		abort(400)

	auth.access_token_expire_utc=0
	g.db.add(auth)

	return jsonify({"message":"Authorization released"})

@app.route("/api/v1/kill", methods=["POST"])
@auth_required
@api()
def oauth_kill_auth(v):

	token=request.headers.get("Authorization").split()[1]

	auth = g.db.query(ClientAuth).filter_by(user_id=v.id, access_token=token).first()
	if not auth:
		abort(404)

	g.db.delete(auth)

	return jsonify({"message":"Authorization released"})
