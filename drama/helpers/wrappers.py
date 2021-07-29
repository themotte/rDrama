from werkzeug.wrappers.response import Response as RespObj
from .get import *
from .alerts import send_notification
from drama.__main__ import app


def get_logged_in_user(db=None):

	if not db:
		db=g.db

	if request.path.startswith("/api/v1"):

		token = request.headers.get("Authorization")
		if not token:

			#let admins hit api/v1 from browser
			# x=request.session.get('user_id')
			# nonce=request.session.get('login_nonce')
			# if not x or not nonce:
			#	 return None, None
			# user=g.db.query(User).filter_by(id=x).first()
			# if not user:
			#	 return None, None
			# if user.admin_level >=3 and nonce>=user.login_nonce:
			#	 return user, None
			return None, None

		token = token.split()
		if len(token) < 2:
			return None, None

		token = token[1]
		if not token:
			return None, None

		client = db.query(ClientAuth).filter(
			ClientAuth.access_token == token).first()
			#ClientAuth.access_token_expire_utc > int(time.time()

		x = (client.user, client) if client else (None, None)


	elif "user_id" in session:

		uid = session.get("user_id")
		nonce = session.get("login_nonce", 0)
		if not uid:
			x= (None, None)
		v = db.query(User).filter_by(
			id=uid).first()

		if v and v.agendaposter_expires_utc and v.agendaposter_expires_utc < g.timestamp:
			v.agendaposter_expires_utc = 0
			v.agendaposter = False

			g.db.add(v)

		if v and (nonce < v.login_nonce):
			x= (None, None)
		else:
			x=(v, None)

	else:
		x=(None, None)

	if x[0]:
		x[0].client=x[1]

	return x

def check_ban_evade(v):

	if not v or not v.ban_evade or v.admin_level > 0:
		return
	
	if random.randint(0,30) < v.ban_evade:
		v.ban(reason="ban evasion")
		send_notification(1046, v, "Your Drama account has been permanently suspended for the following reason:\n\n> ban evasion")

		for post in g.db.query(Submission).filter_by(author_id=v.id).all():
			if post.is_banned:
				continue

			post.is_banned=True
			post.ban_reason="ban evasion"
			g.db.add(post)

			ma=ModAction(
				kind="ban_post",
				user_id=2317,
				target_submission_id=post.id,
				note="ban evasion"
				)
			g.db.add(ma)

		g.db.commit()

		for comment in g.db.query(Comment).filter_by(author_id=v.id).all():
			if comment.is_banned:
				continue

			comment.is_banned=True
			comment.ban_reason="ban evasion"
			g.db.add(comment)

			ma=ModAction(
				kind="ban_comment",
				user_id=2317,
				target_comment_id=comment.id,
				note="ban evasion"
				)
			g.db.add(ma)

		g.db.commit()
		try: abort(403)
		except Exception as e: print(e)

	else:
		v.ban_evade +=1
		g.db.add(v)
		g.db.commit()




# Wrappers
def auth_desired(f):
	# decorator for any view that changes if user is logged in (most pages)

	def wrapper(*args, **kwargs):

		v, c = get_logged_in_user()

		if c:
			kwargs["c"] = c
			
		check_ban_evade(v)

		resp = make_response(f(*args, v=v, **kwargs))
		if v:
			resp.headers.add("Cache-Control", "private")
			resp.headers.add(
				"Access-Control-Allow-Origin",
				app.config["SERVER_NAME"])
		else:
			resp.headers.add("Cache-Control", "public")
		return resp

	wrapper.__name__ = f.__name__
	return wrapper


def auth_required(f):
	# decorator for any view that requires login (ex. settings)

	def wrapper(*args, **kwargs):

		v, c = get_logged_in_user()

		#print(v, c)

		if not v:
			abort(401)
			
		check_ban_evade(v)

		if c:
			kwargs["c"] = c

		g.v = v

		# an ugly hack to make api work
		resp = make_response(f(*args, v=v, **kwargs))

		resp.headers.add("Cache-Control", "private")
		resp.headers.add(
			"Access-Control-Allow-Origin",
			app.config["SERVER_NAME"])
		return resp

	wrapper.__name__ = f.__name__
	return wrapper


def is_not_banned(f):
	# decorator that enforces lack of ban

	def wrapper(*args, **kwargs):

		v, c = get_logged_in_user()

		#print(v, c)

		if not v:
			abort(401)
			
		check_ban_evade(v)

		if v.is_suspended:
			abort(403)

		if c:
			kwargs["c"] = c

		g.v = v

		resp = make_response(f(*args, v=v, **kwargs))
		resp.headers.add("Cache-Control", "private")
		resp.headers.add(
			"Access-Control-Allow-Origin",
			app.config["SERVER_NAME"])
		return resp

	wrapper.__name__ = f.__name__
	return wrapper


# this wrapper takes args and is a bit more complicated
def admin_level_required(x):

	def wrapper_maker(f):

		def wrapper(*args, **kwargs):

			v, c = get_logged_in_user()

			if c:
				return jsonify({"error": "No admin api access"}), 403

			if not v:
				abort(401)

			if v.is_banned:
				abort(403)

			if v.admin_level < x:
				abort(403)

			g.v = v

			response = f(*args, v=v, **kwargs)

			if isinstance(response, tuple):
				resp = make_response(response[0])
			else:
				resp = make_response(response)

			resp.headers.add("Cache-Control", "private")
			resp.headers.add(
				"Access-Control-Allow-Origin",
				app.config["SERVER_NAME"])
			return resp

		wrapper.__name__ = f.__name__
		return wrapper

	return wrapper_maker


def validate_formkey(f):
	"""Always use @auth_required or @admin_level_required above @validate_form"""

	def wrapper(*args, v, **kwargs):

		if not request.path.startswith("/api/v1"):

			submitted_key = request.values.get("formkey", None)

			if not submitted_key: abort(401)

			elif not v.validate_formkey(submitted_key): abort(401)

		return f(*args, v=v, **kwargs)

	wrapper.__name__ = f.__name__
	return wrapper


def no_cors(f):
	"""
	Decorator prevents content being iframe'd
	"""

	def wrapper(*args, **kwargs):

		origin = request.headers.get("Origin", None)

		if origin and origin != "https://" + app.config["SERVER_NAME"] and app.config["FORCE_HTTPS"]==1:

			return "This page may not be embedded in other webpages.", 403

		resp = make_response(f(*args, **kwargs))
		resp.headers.add("Access-Control-Allow-Origin",
						 app.config["SERVER_NAME"]
						 )

		return resp

	wrapper.__name__ = f.__name__
	return wrapper

# wrapper for api-related things that discriminates between an api url
# and an html url for the same content
# f should return {'api':lambda:some_func(), 'html':lambda:other_func()}


def api(*scopes, no_ban=False):

	def wrapper_maker(f):

		def wrapper(*args, **kwargs):

			if request.path.startswith(('/api/v1','/api/v2')):

				v = kwargs.get('v')

				result = f(*args, **kwargs)

				if isinstance(result, dict):
					resp = result['api']()
				else:
					resp = result

				if not isinstance(resp, RespObj):
					resp = make_response(resp)

				resp.headers.add("Cache-Control", "private")
				resp.headers.add(
					"Access-Control-Allow-Origin",
					app.config["SERVER_NAME"])
				return resp

			else:

				result = f(*args, **kwargs)

				if not isinstance(result, dict):
					return result

				try:
					if request.path.startswith('/inpage/'):
						return result['inpage']()
					elif request.path.startswith(('/api/vue/','/test/')):
						return result['api']()
					else:
						return result['html']()
				except KeyError:
					return result

		wrapper.__name__ = f.__name__
		return wrapper

	return wrapper_maker