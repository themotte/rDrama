from .get import *
from .alerts import *
from files.helpers.const import *
from files.__main__ import db_session
from random import randint

def get_logged_in_user():
	if not (hasattr(g, 'db') and g.db): g.db = db_session()

	v = None

	token = request.headers.get("Authorization","").strip()
	if token:
		client = g.db.query(ClientAuth).filter(ClientAuth.access_token == token).one_or_none()
		if client: 
			v = client.user
			v.client = client
	else:
		lo_user = session.get("lo_user")
		if lo_user:
			id = int(lo_user)
			v = g.db.query(User).filter_by(id=id).one_or_none()
			if v:
				nonce = session.get("login_nonce", 0)
				if nonce < v.login_nonce or v.id != id: abort(401)

				if request.method != "GET":
					submitted_key = request.values.get("formkey")
					if not submitted_key: abort(401)
					if not v.validate_formkey(submitted_key): abort(401)

				v.client = None


	if request.method.lower() != "get" and app.config['SETTINGS']['Read-only mode'] and not (v and v.admin_level):
		abort(403)

	if v and v.patron:
		if request.content_length and request.content_length > 16 * 1024 * 1024: abort(413)
	elif request.content_length and request.content_length > 8 * 1024 * 1024: abort(413)

	return v

def check_ban_evade(v):
	if v and not v.patron and v.admin_level < 2 and v.ban_evade and not v.unban_utc:
		v.shadowbanned = "AutoJanny"
		g.db.add(v)
		g.db.commit()

def auth_desired(f):
	def wrapper(*args, **kwargs):

		v = get_logged_in_user()

		check_ban_evade(v)

		g.v = v
		return make_response(f(*args, v=v, **kwargs))

	wrapper.__name__ = f.__name__
	return wrapper


def auth_required(f):

	def wrapper(*args, **kwargs):

		v = get_logged_in_user()
		if not v: abort(401)

		check_ban_evade(v)

		g.v = v
		return make_response(f(*args, v=v, **kwargs))

	wrapper.__name__ = f.__name__
	return wrapper


def is_not_permabanned(f):

	def wrapper(*args, **kwargs):

		v = get_logged_in_user()

		if not v: abort(401)
		
		check_ban_evade(v)

		if v.is_banned and v.unban_utc == 0:
			return {"error": "Interal server error"}, 500

		g.v = v
		return make_response(f(*args, v=v, **kwargs))

	wrapper.__name__ = f.__name__
	return wrapper


def admin_level_required(x):

	def wrapper_maker(f):

		def wrapper(*args, **kwargs):

			v = get_logged_in_user()

			if not v: abort(401)

			if v.admin_level < x: abort(403)
			
			g.v = v
			return make_response(f(*args, v=v, **kwargs))

		wrapper.__name__ = f.__name__
		return wrapper

	return wrapper_maker