import functools
import time

import sqlalchemy

from files.helpers.alerts import *
from files.helpers.config.const import *
from files.helpers.get import *
from files.helpers.moderation import shadowban_set
from files.routes.importstar import *
from files.__main__ import app, cache, db_session


def get_logged_in_user():
	if hasattr(g, 'v'):
		return g.v

	if not (hasattr(g, 'db') and g.db):  # pragma: no cover (only the chat service's socket events, which stay out of the spec, arrive without before_request)
		# Create a new session instead of reusing the thread-local scoped session
		g.db = db_session.session_factory()

	v = None

	token = request.headers.get("Authorization", "").strip()
	if token:
		client = g.db.query(ClientAuth).join(ClientAuth.application).filter(ClientAuth.access_token == token, OauthApp.client_id != None).one_or_none()
		if client: 
			v = client.user
			v.client = client
	else:
		lo_user = session.get("lo_user")
		if lo_user:
			id = int(lo_user)
			v = g.db.get(User, id)
			if v:
				v.client = None
				nonce = session.get("login_nonce", 0)
				if nonce != v.login_nonce:
					session.pop("lo_user")
					v = None

				if v and request.method != "GET":
					submitted_key = request.values.get("formkey")
					if not submitted_key and request.is_json:
						json = request.get_json(silent=True)
						if json and type(json) is dict:
							submitted_key = json.get('formkey')
					if not v.validate_formkey(submitted_key):
						v = None
			else:
				session.pop("lo_user")

	if request.content_length and request.content_length > 8 * 1024 * 1024:
		abort(413)

	if not session.get("session_id"):
		session.permanent = True
		session["session_id"] = secrets.token_hex(49)

	if v: _end_expired_ban(v)

	g.v = v
	return v


def _end_expired_ban(v):
	'''Ends `v`'s temporary ban once it has run out, with its ban-evasion mark, telling them; concurrent requests end it once.'''
	if not (v.is_banned and v.unban_utc and v.unban_utc < time.time()): return
	ended = g.db.execute(sqlalchemy.update(User).where(User.id == v.id, User.is_banned != 0, User.unban_utc == v.unban_utc).values(is_banned=0, unban_utc=0, ban_evade=0)).rowcount
	if ended: send_repeatable_notification(v.id, "You have been unbanned!")
	g.db.commit()


def check_ban_evade(v):
	if v and v.account_admin_level < 2 and v.ban_evade and not v.unban_utc:
		shadowban_set(v, "AutoJanny")
		g.db.add(v)
		g.db.commit()


@app.template_global()
def age_unconfirmed(post, v) -> bool:
	'''Whether the 18+ `post` must wait for the viewer to confirm their age: they're not an 18+ user and haven't confirmed recently.'''
	return post.over_18 and not (v and v.over_18) and session.get('over_18', 0) < int(time.time())


def refuse_while_suspended(v):
	'''Suspended users can't change anything other users see.'''
	if v.is_suspended: abort(403, "You can't perform this action while banned.")


def refuse_api_client(v):
	'''Refuses (403) a request made by an API app acting for `v`, for what only the person, in the account's own browser, may do.'''
	if v.client: abort(403, "API clients can't do this")


def auth_desired(f):
	@functools.wraps(f)
	def wrapper(*args, **kwargs):
		v = get_logged_in_user()
		check_ban_evade(v)
		return make_response(f(*args, v=v, **kwargs))
	return wrapper


def auth_required(f):
	@functools.wraps(f)
	def wrapper(*args, **kwargs):
		v = get_logged_in_user()
		if not v: abort(401)
		check_ban_evade(v)
		return make_response(f(*args, v=v, **kwargs))
	return wrapper


def is_not_permabanned(f):
	@functools.wraps(f)
	def wrapper(*args, **kwargs):
		v = get_logged_in_user()
		if not v: abort(401)
		check_ban_evade(v)
		if v.is_suspended_permanently:
			abort(403, "You are permanently banned")
		return make_response(f(*args, v=v, **kwargs))
	return wrapper


def admin_level_required(x):
	def wrapper_maker(f):
		@functools.wraps(f)
		def wrapper(*args, **kwargs):
			v = get_logged_in_user()
			if not v: abort(401)
			if v.client: abort(403, "Admin actions aren't available to API clients")
			if v.admin_level < x: abort(403)
			# Admins read while suspended, but don't act as admins
			if request.method not in ("GET", "HEAD"): refuse_while_suspended(v)
			return make_response(f(*args, v=v, **kwargs))
		return wrapper
	return wrapper_maker
