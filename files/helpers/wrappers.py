from .get import *
from .alerts import *
from files.helpers.const import *
from files.__main__ import db_session
from random import randint

def get_logged_in_user():
	if not (hasattr(g, 'db') and g.db): g.db = db_session()

	token = request.headers.get("Authorization","").strip()
	if token:
		client = g.db.query(ClientAuth).filter(ClientAuth.access_token == token).one_or_none()

		if not client: return None

		v = client.user
		v.client = client
	else:
		lo_user = session.get("lo_user")
		if not lo_user: return None

		nonce = session.get("login_nonce", 0)
		v = g.db.query(User).filter_by(id=lo_user).one_or_none()

		if not v or nonce < v.login_nonce: return None
		v.client = None

		if request.method != "GET":
			submitted_key = request.values.get("formkey")
			if not submitted_key: abort(401)
			elif not v.validate_formkey(submitted_key): abort(401)

	
	if v.patron_utc and v.patron_utc < time.time():
		v.patron = 0
		v.patron_utc = 0
		send_repeatable_notification(v.id, "Your paypig status has expired!")
		g.db.add(v)
		g.db.commit()

	if v.unban_utc and v.unban_utc < time.time():
		v.is_banned = 0
		v.unban_utc = 0
		v.ban_evade = 0
		send_repeatable_notification(v.id, "You have been unbanned!")
		g.db.add(v)
		g.db.commit()

	if v.hidevotedon: posts = [x for x in posts if not hasattr(x, 'voted') or not x.voted]

	if v.agendaposter_expires_utc and v.agendaposter_expires_utc < time.time():
		v.agendaposter_expires_utc = 0
		v.agendaposter = None
		send_repeatable_notification(v.id, "Your chud theme has expired!")
		g.db.add(v)
		badge = v.has_badge(26)
		if badge: g.db.delete(badge)
		g.db.commit()

	if v.flairchanged and v.flairchanged < time.time():
		v.flairchanged = None
		send_repeatable_notification(v.id, "Your flair lock has expired. You can now change your flair!")
		g.db.add(v)
		badge = v.has_badge(96)
		if badge: g.db.delete(badge)
		g.db.commit()

	if v.marseyawarded and v.marseyawarded < time.time():
		v.marseyawarded = None
		send_repeatable_notification(v.id, "Your marsey award has expired!")
		g.db.add(v)
		badge = v.has_badge(98)
		if badge: g.db.delete(badge)
		g.db.commit()

	if v.longpost and v.longpost < time.time():
		v.longpost = None
		send_repeatable_notification(v.id, "Your pizzashill award has expired!")
		g.db.add(v)
		badge = v.has_badge(97)
		if badge: g.db.delete(badge)
		g.db.commit()

	if v.bird and v.bird < time.time():
		v.bird = None
		send_repeatable_notification(v.id, "Your bird site award has expired!")
		g.db.add(v)
		badge = v.has_badge(95)
		if badge: g.db.delete(badge)
		g.db.commit()

	if v.progressivestack and v.progressivestack < time.time():
		v.progressivestack = None
		send_repeatable_notification(v.id, "Your progressive stack has expired!")
		g.db.add(v)
		badge = v.has_badge(94)
		if badge: g.db.delete(badge)
		g.db.commit()

	if v.rehab and v.rehab < time.time():
		v.rehab = None
		send_repeatable_notification(v.id, "Your rehab has finished!")
		g.db.add(v)
		badge = v.has_badge(109)
		if badge: g.db.delete(badge)
		g.db.commit()

	return v

def check_ban_evade(v):
	if v and not v.patron and v.admin_level == 0 and v.ban_evade and not v.unban_utc:
		if randint(0,30) < v.ban_evade: v.shadowbanned = "AutoJanny"
		else: v.ban_evade +=1
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