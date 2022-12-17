from .get import *
from .alerts import *
from files.helpers.const import *
from files.__main__ import db_session
from random import randint
import user_agents
import time

def get_logged_in_user():
	if hasattr(g, 'v'):
		return g.v

	if not (hasattr(g, 'db') and g.db):
		g.db = db_session()

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
			v = g.db.query(User).get(id)
			if v:
				v.client = None
				nonce = session.get("login_nonce", 0)
				if nonce < v.login_nonce or v.id != id:
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

	if request.method.lower() != "get" \
			and app.config['SETTINGS']['Read-only mode'] \
			and not (v and v.admin_level):
		abort(403)

	if request.content_length and request.content_length > 8 * 1024 * 1024:
		abort(413)

	if not session.get("session_id"):
		session.permanent = True
		session["session_id"] = secrets.token_hex(49)

	# Active User Counters
	loggedin = cache.get(f'{SITE}_loggedin') or {}
	loggedout = cache.get(f'{SITE}_loggedout') or {}

	timestamp = int(time.time())
	if v:
		if session["session_id"] in loggedout:
			del loggedout[session["session_id"]]
		loggedin[v.id] = timestamp
	else:
		ua = str(user_agents.parse(g.agent))
		if 'spider' not in ua.lower() and 'bot' not in ua.lower():
			loggedout[session["session_id"]] = (timestamp, ua)

	g.loggedin_counter = len([x for x in loggedin.values() \
		if (timestamp - x) < LOGGEDIN_ACTIVE_TIME])
	g.loggedout_counter = len([x for x in loggedout.values() \
		if (timestamp - x[0]) < LOGGEDIN_ACTIVE_TIME])
	cache.set(f'{SITE}_loggedin', loggedin)
	cache.set(f'{SITE}_loggedout', loggedout)

	g.v = v
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

		return make_response(f(*args, v=v, **kwargs))

	wrapper.__name__ = f.__name__
	return wrapper


def auth_required(f):

	def wrapper(*args, **kwargs):
		v = get_logged_in_user()
		if not v: abort(401)

		check_ban_evade(v)

		return make_response(f(*args, v=v, **kwargs))

	wrapper.__name__ = f.__name__
	return wrapper


def is_not_permabanned(f):

	def wrapper(*args, **kwargs):
		v = get_logged_in_user()
		if not v: abort(401)
		
		check_ban_evade(v)

		if v.is_suspended_permanently:
			abort(403, "You are permanently banned")

		return make_response(f(*args, v=v, **kwargs))

	wrapper.__name__ = f.__name__
	return wrapper


def admin_level_required(x):

	def wrapper_maker(f):

		def wrapper(*args, **kwargs):
			v = get_logged_in_user()
			if not v: abort(401)

			if v.admin_level < x: abort(403)

			return make_response(f(*args, v=v, **kwargs))

		wrapper.__name__ = f.__name__
		return wrapper

	return wrapper_maker
