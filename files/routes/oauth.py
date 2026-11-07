from sqlalchemy.dialects import postgresql

from files.__main__ import app, limiter
from files.classes import *
from files.helpers.alerts import *
from files.helpers.config.const import *
from files.helpers.get import *
from files.helpers.listing import request_page
from files.helpers.wrappers import *
from files.routes.importstar import *


@app.get("/authorize")
@auth_required
def authorize_prompt(v):
	refuse_api_client(v)
	application = _app_by_client_id(request.values.get("client_id"))
	if not application: return {"oauth_error": "Invalid `client_id`"}, 401
	return render_template("oauth.html", v=v, application=application)


@app.post("/authorize")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def authorize(v):
	refuse_api_client(v)
	application = _app_by_client_id(request.values.get("client_id"))
	if not application: return {"oauth_error": "Invalid `client_id`"}, 401
	access_token = _authorization(application, v)
	g.db.commit()

	return redirect(f"{application.redirect_uri}?token={access_token}")


def _app_by_client_id(client_id: Optional[str]) -> Optional[OauthApp]:
	'''The approved app whose client id is `client_id`; pending apps have none, so a missing id matches nothing.'''
	if not client_id: return None
	return g.db.query(OauthApp).filter(OauthApp.client_id == client_id).one_or_none()


def _app(aid: str) -> OauthApp:
	'''The app with the id `aid` from the URL, else 404.'''
	app_id = parse_id(aid)
	app = g.db.get(OauthApp, app_id) if app_id else None
	if not app: abort(404)
	return app


def _app_owned(v: User, aid: str) -> OauthApp:
	'''The app with the id `aid` from the URL, which only its owner may manage.'''
	app = _app(aid)
	if app.author_id != v.id: abort(403)
	return app


def _authorization(application: OauthApp, user: User) -> str:
	'''The access token `user` holds for `application`, created if they hold none; concurrent requests agree on one.'''
	g.db.execute(postgresql.insert(ClientAuth).values(oauth_client=application.id, user_id=user.id, access_token=secrets.token_urlsafe(128)[:128]).on_conflict_do_nothing(index_elements=[ClientAuth.user_id, ClientAuth.oauth_client]))
	return g.db.query(ClientAuth.access_token).filter_by(oauth_client=application.id, user_id=user.id).scalar()


@app.post("/api_keys")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@is_not_permabanned
def request_api_keys(v):
	refuse_api_client(v)
	new_app = OauthApp(
		app_name=request.values.get('name').replace('<','').replace('>',''),
		redirect_uri=request.values.get('redirect_uri'),
		author_id=v.id,
		description=request.values.get("description")[:256]
	)

	g.db.add(new_app)

	body = f"@{v.username} has requested API keys for `{request.values.get('name')}`. You can approve or deny the request [here](/admin/apps)."

	body_html = sanitize(body)


	new_comment = Comment(author_id=NOTIFICATIONS_ID,
						  parent_submission=None,
						  level=1,
						  body_html=body_html,
						  sentto=MODMAIL_ID,
						  distinguish_level=6,
						  state_mod=StateMod.VISIBLE,
						  )
	g.db.add(new_comment)
	g.db.flush()

	new_comment.top_comment_id = new_comment.id

	notify_modmail(new_comment.id, v)


	g.db.commit()

	return redirect('/settings/apps')


@app.post("/delete_app/<aid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def delete_oauth_app(v, aid):
	refuse_api_client(v)
	app = _app_owned(v, aid)

	for auth in g.db.query(ClientAuth).filter_by(oauth_client=app.id).all():
		g.db.delete(auth)

	g.db.delete(app)

	g.db.commit()

	return redirect('/apps')


@app.post("/edit_app/<aid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@is_not_permabanned
def edit_oauth_app(v, aid):
	refuse_api_client(v)
	app = _app_owned(v, aid)

	app.redirect_uri = request.values.get('redirect_uri')
	app.app_name = request.values.get('name')
	app.description = request.values.get("description")[:256]

	g.db.add(app)

	g.db.commit()

	return redirect('/settings/apps')


@app.post("/oauth/rescind/<aid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def rescind_authorization(v, aid):
	refuse_api_client(v)
	app_id = parse_id(aid)
	authorization = g.db.get(ClientAuth, (v.id, app_id)) if app_id else None
	if not authorization: abort(404)
	g.db.delete(authorization)
	g.db.commit()
	return {"message": "Authorization revoked"}


@app.post("/admin/app/approve/<aid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@admin_level_required(3)
def admin_app_approve(v, aid):
	app = _app(aid)
	user = app.author

	app.client_id = secrets.token_urlsafe(64)[:64]
	g.db.add(app)

	access_token = secrets.token_urlsafe(128)[:128]
	new_auth = ClientAuth(
		oauth_client = app.id,
		user_id = user.id,
		access_token=access_token
	)

	g.db.add(new_auth)

	send_repeatable_notification(user.id, f"@{v.username} has approved your application `{app.app_name}`. Your access token is in [your apps settings](/settings/apps).\nPlease check the guide [here](/api) if you don't know what to do next.")

	ma = ModAction(
		kind="approve_app",
		user_id=v.id,
		target_user_id=user.id,
	)
	g.db.add(ma)

	g.db.commit()

	return {"message": "Application approved"}


@app.post("/admin/app/revoke/<aid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@admin_level_required(2)
def admin_app_revoke(v, aid):
	app = _app(aid)
	for auth in g.db.query(ClientAuth).filter_by(oauth_client=app.id).all(): g.db.delete(auth)

	send_repeatable_notification(app.author.id, f"@{v.username} has revoked your application `{app.app_name}`.")

	g.db.delete(app)

	ma = ModAction(
		kind="revoke_app",
		user_id=v.id,
		target_user_id=app.author.id,
	)
	g.db.add(ma)

	g.db.commit()

	return {"message": "App revoked"}


@app.post("/admin/app/reject/<aid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@admin_level_required(2)
def admin_app_reject(v, aid):
	app = _app(aid)
	for auth in g.db.query(ClientAuth).filter_by(oauth_client=app.id).all(): g.db.delete(auth)

	send_repeatable_notification(app.author.id, f"@{v.username} has rejected your application `{app.app_name}`.")

	g.db.delete(app)

	ma = ModAction(
		kind="reject_app",
		user_id=v.id,
		target_user_id=app.author.id,
	)
	g.db.add(ma)

	g.db.commit()

	return {"message": "App rejected"}


@app.get("/admin/app/<aid>")
@admin_level_required(2)
def admin_app_id(v, aid):
	oauth = _app(aid)

	pids=oauth.idlist(page=request_page())

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
@admin_level_required(2)
def admin_app_id_comments(v, aid):
	oauth = _app(aid)

	cids=oauth.comments_idlist(page=request_page())

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
@admin_level_required(2)
def admin_apps_list(v):
	apps = g.db.query(OauthApp).order_by(OauthApp.id.desc()).all()

	return render_template("admin/apps.html", v=v, apps=apps)


@app.post("/oauth/reroll/<aid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def reroll_oauth_tokens(aid, v):
	refuse_api_client(v)
	a = _app_owned(v, aid)
	if a.state != OauthAppState.APPROVED: abort(409, "Only approved apps have a client ID")

	a.client_id = secrets.token_urlsafe(64)[:64]
	g.db.add(a)

	g.db.commit()

	return {"message": "Client ID Rerolled", "id": a.client_id}
