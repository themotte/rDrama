from sqlalchemy import func
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


def _app_fields() -> tuple[str, str, str]:
	'''The name, redirect URI and description a request or edit gives an app, else 400.'''
	name, redirect_uri, description = (request.values.get(field) for field in ("name", "redirect_uri", "description"))
	if name is None or redirect_uri is None or description is None: abort(400, "Name, redirect URI and description are required")
	name, redirect_uri = name.strip(), redirect_uri.strip()
	if not 0 < len(name) <= 50: abort(400, "The name must be 1 to 50 characters long")
	if not 0 < len(redirect_uri) <= 4096: abort(400, "The redirect URI must be 1 to 4096 characters long")
	return name, redirect_uri, description[:256]


def _app(aid: str, lock: bool = False) -> OauthApp:
	'''The app with the id `aid` from the URL, else 404. Actions that change an app lock it first, so concurrent ones see each other's outcome before checking its state.'''
	app_id = parse_id(aid)
	query = g.db.query(OauthApp).filter_by(id=app_id)
	if lock: query = query.with_for_update().populate_existing()
	app = query.one_or_none() if app_id else None
	if not app: abort(404)
	return app


def _app_owned(v: User, aid: str) -> OauthApp:
	'''The app with the id `aid` from the URL, locked for its owner, the only one who may manage it, to change; to them a revoked app is gone (404).'''
	app = _app(aid, lock=True)
	if app.state == OauthAppState.REVOKED: abort(404)
	if app.author_id != v.id: abort(403)
	return app


def _withdraw(app: OauthApp):
	'''Ends every authorization of `app` (locked by the caller) and deletes it, except an app whose tokens made posts or comments: that is kept, revoked, so admins can still see where they came from.'''
	g.db.query(ClientAuth).filter_by(oauth_client=app.id).delete()
	if g.db.query(Submission.id).filter_by(app_id=app.id).first() or g.db.query(Comment.id).filter_by(app_id=app.id).first():
		app.client_id = None
		app.revoked_utc = func.now()
	else:
		g.db.delete(app)


def _authorization(application: OauthApp, user: User) -> str:
	'''The access token `user` holds for `application`, created if they hold none; concurrent requests agree on one.'''
	g.db.execute(postgresql.insert(ClientAuth).values(oauth_client=application.id, user_id=user.id, access_token=secrets.token_urlsafe(128)[:128]).on_conflict_do_nothing(index_elements=[ClientAuth.user_id, ClientAuth.oauth_client]))
	return g.db.query(ClientAuth.access_token).filter_by(oauth_client=application.id, user_id=user.id).scalar()


@app.post("/api_keys")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def request_api_keys(v):
	refuse_api_client(v)
	refuse_while_suspended(v)
	name, redirect_uri, description = _app_fields()
	new_app = OauthApp(app_name=name, redirect_uri=redirect_uri, author_id=v.id, description=description)

	g.db.add(new_app)

	body = f"@{v.username} has requested API keys for `{name}`. You can approve or deny the request [here](/admin/apps)."

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
	_withdraw(app)
	g.db.commit()

	return redirect('/settings/apps')


@app.post("/edit_app/<aid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def edit_oauth_app(v, aid):
	refuse_api_client(v)
	app = _app_owned(v, aid)
	refuse_while_suspended(v)

	app.app_name, app.redirect_uri, app.description = _app_fields()

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
	app = _app(aid, lock=True)
	if app.state != OauthAppState.PENDING: abort(409, "Only pending apps can be approved")
	user = app.author

	app.client_id = secrets.token_urlsafe(64)[:64]
	_authorization(app, user)

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
	app = _app(aid, lock=True)
	if app.state != OauthAppState.APPROVED: abort(409, "Only approved apps can be revoked")
	owner = app.author
	_withdraw(app)

	send_repeatable_notification(owner.id, f"@{v.username} has revoked your application `{app.app_name}`.")

	ma = ModAction(
		kind="revoke_app",
		user_id=v.id,
		target_user_id=owner.id,
	)
	g.db.add(ma)

	g.db.commit()

	return {"message": "App revoked"}


@app.post("/admin/app/reject/<aid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@admin_level_required(2)
def admin_app_reject(v, aid):
	app = _app(aid, lock=True)
	if app.state != OauthAppState.PENDING: abort(409, "Only pending apps can be rejected")
	owner = app.author
	_withdraw(app)

	send_repeatable_notification(owner.id, f"@{v.username} has rejected your application `{app.app_name}`.")

	ma = ModAction(
		kind="reject_app",
		user_id=v.id,
		target_user_id=owner.id,
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
