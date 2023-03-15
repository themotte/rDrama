
from pathlib import Path
import gevent.monkey
gevent.monkey.patch_all()
from os import environ, path
import secrets
from files.helpers.strings import bool_from_string
from flask import *
from flask_caching import Cache
from flask_limiter import Limiter
from flask_compress import Compress
from flask_mail import Mail
import flask_profiler
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import *
import gevent
import redis
import time
from sys import stdout, argv
import faulthandler
import json


app = Flask(__name__, template_folder='templates')
app.url_map.strict_slashes = False
app.jinja_env.cache = {}
app.jinja_env.auto_reload = True
faulthandler.enable()

if bool_from_string(environ.get("ENFORCE_PRODUCTION", True)) and app.debug:
	raise ValueError("Debug mode is not allowed! If this is a dev environment, please set ENFORCE_PRODUCTION to false")

if environ.get("SITE_ID") is None:
	from dotenv import load_dotenv
	load_dotenv(dotenv_path=Path("env"))

if environ.get("FLASK_PROFILER_ENDPOINT"):
	app.config["flask_profiler"] = {
		"enabled": True,
		"storage": {
			"engine": "sqlalchemy",
		},
		"basicAuth": {
			"enabled": True,
			"username": environ.get("FLASK_PROFILER_USERNAME"),
			"password": environ.get("FLASK_PROFILER_PASSWORD"),
		},
		"endpointRoot": environ.get("FLASK_PROFILER_ENDPOINT"),
	}

	profiler = flask_profiler.Profiler()
	profiler.init_app(app)

try:
	from easy_profile import EasyProfileMiddleware
	from jinja2.utils import internal_code

	import inspect as inspectlib
	import linecache
	
	def jinja_unmangle_stacktrace():
		rewritten_frames = []

		for record in inspectlib.stack():
			# Skip jinja internalcode frames
			if record.frame.f_code in internal_code:
				continue
			
			filename = record.frame.f_code.co_filename
			lineno = record.frame.f_lineno
			name = record.frame.f_code.co_name

			template = record.frame.f_globals.get("__jinja_template__")
			if template is not None:
				lineno = template.get_corresponding_lineno(lineno)

			line = linecache.getline(filename, lineno).strip()

			rewritten_frames.append(f'  File "{filename}", line {lineno}, {name}\n    {line}\n')

		return "".join(rewritten_frames)

	app.wsgi_app = EasyProfileMiddleware(
		app.wsgi_app,
		stack_callback = jinja_unmangle_stacktrace)
except ModuleNotFoundError:
	# failed to import, just keep on going
	pass

app.config["SITE_ID"]=environ.get("SITE_ID").strip()
app.config["SITE_TITLE"]=environ.get("SITE_TITLE").strip()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DATABASE_URL'] = environ.get("DATABASE_URL", "postgresql://postgres@localhost:5432")
app.config['SECRET_KEY'] = environ.get('MASTER_KEY')
app.config["SERVER_NAME"] = environ.get("DOMAIN").strip()
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 if app.debug else 3153600
app.config["SESSION_COOKIE_NAME"] = "session_" + environ.get("SITE_ID").strip().lower()
app.config["VERSION"] = "1.0.0"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config["SESSION_COOKIE_SECURE"] = bool(environ.get('SESSION_COOKIE_SECURE', "localhost" not in environ.get("DOMAIN")))
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 365
app.config["DEFAULT_COLOR"] = environ.get("DEFAULT_COLOR", "ffffff").strip()
app.config["DEFAULT_THEME"] = "TheMotte"
app.config["FORCE_HTTPS"] = 1
app.config["UserAgent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
app.config["HCAPTCHA_SITEKEY"] = environ.get("HCAPTCHA_SITEKEY","").strip()
app.config["HCAPTCHA_SECRET"] = environ.get("HCAPTCHA_SECRET","").strip()
app.config["SPAM_SIMILARITY_THRESHOLD"] = float(environ.get("SPAM_SIMILARITY_THRESHOLD", 0.5))
app.config["SPAM_URL_SIMILARITY_THRESHOLD"] = float(environ.get("SPAM_URL_SIMILARITY_THRESHOLD", 0.1))
app.config["SPAM_SIMILAR_COUNT_THRESHOLD"] = int(environ.get("SPAM_SIMILAR_COUNT_THRESHOLD", 10))
app.config["COMMENT_SPAM_SIMILAR_THRESHOLD"] = float(environ.get("COMMENT_SPAM_SIMILAR_THRESHOLD", 0.5))
app.config["COMMENT_SPAM_COUNT_THRESHOLD"] = int(environ.get("COMMENT_SPAM_COUNT_THRESHOLD", 10))
app.config["CACHE_TYPE"] = "RedisCache"
app.config["CACHE_REDIS_URL"] = environ.get("REDIS_URL", "redis://localhost")
app.config['MAIL_SERVER'] = environ.get("MAIL_SERVER", "").strip()
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = environ.get("MAIL_USERNAME", "").strip()
app.config['MAIL_PASSWORD'] = environ.get("MAIL_PASSWORD", "").strip()
app.config['DESCRIPTION'] = environ.get("DESCRIPTION", "DESCRIPTION GOES HERE").strip()
app.config['SETTINGS'] = {}
app.config['SQLALCHEMY_DATABASE_URI'] = app.config['DATABASE_URL']
app.config['MENTION_LIMIT'] = int(environ.get('MENTION_LIMIT', 100))
app.config['MULTIMEDIA_EMBEDDING_ENABLED'] = environ.get('MULTIMEDIA_EMBEDDING_ENABLED', "false").lower() == "true"
app.config['RESULTS_PER_PAGE_COMMENTS'] = int(environ.get('RESULTS_PER_PAGE_COMMENTS',50))
app.config['SCORE_HIDING_TIME_HOURS'] = int(environ.get('SCORE_HIDING_TIME_HOURS'))
app.config['ENABLE_SERVICES'] = bool_from_string(environ.get('ENABLE_SERVICES', False))

app.config['DBG_VOLUNTEER_PERMISSIVE'] = bool_from_string(environ.get('DBG_VOLUNTEER_PERMISSIVE', False))
app.config['VOLUNTEER_JANITOR_ENABLE'] = bool_from_string(environ.get('VOLUNTEER_JANITOR_ENABLE', True))

r=redis.Redis(host=environ.get("REDIS_URL", "redis://localhost"), decode_responses=True, ssl_cert_reqs=None)

def get_remote_addr():
	with app.app_context():
		return request.headers.get('X-Real-IP', default='127.0.0.1')

app.config['RATE_LIMITER_ENABLED'] = not bool_from_string(environ.get('DBG_LIMITER_DISABLED', False))
if not app.config['RATE_LIMITER_ENABLED']:
	print("Rate limiter disabled in debug mode!")
limiter = Limiter(
	key_func=get_remote_addr,
	app=app,
	default_limits=["3/second;30/minute;200/hour;1000/day"],
	application_limits=["10/second;200/minute;5000/hour;10000/day"],
	storage_uri=environ.get("REDIS_URL", "redis://localhost"),
	auto_check=False,
	enabled=app.config['RATE_LIMITER_ENABLED'],
)

engine = create_engine(app.config['DATABASE_URL'])

db_session = scoped_session(sessionmaker(bind=engine, autoflush=False))

cache = Cache(app)
Compress(app)
mail = Mail(app)

@app.before_request
def before_request():
	with open('site_settings.json', 'r') as f:
		app.config['SETTINGS'] = json.load(f)

	if request.host != app.config["SERVER_NAME"]:
		return {"error": "Unauthorized host provided."}, 403

	if not app.config['SETTINGS']['Bots'] and request.headers.get("Authorization"):
		abort(403, "Bots are currently not allowed")

	g.agent = request.headers.get("User-Agent")
	if not g.agent:
		return 'Please use a "User-Agent" header!', 403

	ua = g.agent.lower()
	g.debug = app.debug
	g.webview = ('; wv) ' in ua)
	g.inferior_browser = (
		'iphone' in ua or
		'ipad' in ua or
		'ipod' in ua or
		'mac os' in ua or
		' firefox/' in ua)
	g.timestamp = int(time.time())

	limiter.check()

	g.db = db_session()


@app.teardown_appcontext
def teardown_request(error):
	if hasattr(g, 'db') and g.db:
		g.db.close()
	stdout.flush()

@app.after_request
def after_request(response):
	response.headers.add("Strict-Transport-Security", "max-age=31536000")
	response.headers.add("X-Frame-Options", "deny")
	return response

if "load_chat" in argv:
	from files.routes.chat import *
else:
	from files.routes import *
