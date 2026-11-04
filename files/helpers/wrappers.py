import functools
import time

from files.helpers.alerts import *
from files.helpers.config.const import *
from files.helpers.config.environment import SITE
from files.helpers.get import *
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
		client = g.db.query(ClientAuth).filter(ClientAuth.access_token == token).one_or_none()
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

	g.v = v
	return v


def check_ban_evade(v):
	if v and v.account_admin_level < 2 and v.ban_evade and not v.unban_utc:
		v.shadowbanned = "AutoJanny"
		g.db.add(v)
		g.db.commit()


def refuse_while_suspended(v):
	'''Suspended users can't change anything other users see.'''
	if v.is_suspended: abort(403, "You can't perform this action while banned.")


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
			return make_response(f(*args, v=v, **kwargs))
		return wrapper
	return wrapper_maker
