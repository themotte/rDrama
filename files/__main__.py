import gevent.monkey

gevent.monkey.patch_all()

# ^ special case: in general imports should go
# stdlib - externals - internals, but gevent does monkey patching for stdlib 
# functions so we want to monkey patch before importing other things

import faulthandler
from os import environ
from pathlib import Path
from sys import argv

import flask
import flask_caching
import flask_compress
import flask_limiter
import flask_mail
import flask_profiler
import gevent
import redis
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from files.helpers.const import *
from files.helpers.config.stateful import const_initialize
from files.helpers.strings import bool_from_string

app = flask.Flask(__name__, template_folder='templates')
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
	import inspect as inspectlib
	import linecache

	from easy_profile import EasyProfileMiddleware
	from jinja2.utils import internal_code
	
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

from files.helpers.config.environment import *

app.config["SITE_ID"] = SITE_ID
app.config["SITE_TITLE"] = SITE_TITLE
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DATABASE_URL'] = environ.get("DATABASE_URL", "postgresql://postgres@localhost:5432")
app.config['SECRET_KEY'] = SECRET_KEY
app.config["SERVER_NAME"] = SERVER_NAME
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 if app.debug else 3153600
app.config["SESSION_COOKIE_NAME"] = f'session_{SITE_ID}'
app.config["VERSION"] = "1.0.0"
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config["SESSION_COOKIE_SECURE"] = SESSION_COOKIE_SECURE
app.config["SESSION_COOKIE_SAMESITE"] = SESSION_COOKIE_SAMESITE
app.config["PERMANENT_SESSION_LIFETIME"] = PERMANENT_SESSION_LIFETIME
app.config["DEFAULT_COLOR"] = DEFAULT_COLOR
app.config["DEFAULT_THEME"] = "TheMotte"
app.config["FORCE_HTTPS"] = 1
app.config["UserAgent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
app.config["HCAPTCHA_SITEKEY"] = environ.get("HCAPTCHA_SITEKEY","").strip()
app.config["HCAPTCHA_SECRET"] = environ.get("HCAPTCHA_SECRET","").strip()
app.config["SPAM_SIMILARITY_THRESHOLD"] = SPAM_SIMILARITY_THRESHOLD
app.config["SPAM_URL_SIMILARITY_THRESHOLD"] = SPAM_URL_SIMILARITY_THRESHOLD
app.config["SPAM_SIMILAR_COUNT_THRESHOLD"] = SPAM_SIMILAR_COUNT_THRESHOLD
app.config["COMMENT_SPAM_SIMILAR_THRESHOLD"] = COMMENT_SPAM_SIMILAR_THRESHOLD
app.config["COMMENT_SPAM_COUNT_THRESHOLD"] = COMMENT_SPAM_COUNT_THRESHOLD
app.config["CACHE_TYPE"] = "RedisCache"
app.config["CACHE_REDIS_URL"] = environ.get("REDIS_URL", "redis://localhost")
app.config['MAIL_SERVER'] = environ.get("MAIL_SERVER", "").strip()
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
app.config['DESCRIPTION'] = DESCRIPTION
app.config['SETTINGS'] = {}
app.config['SQLALCHEMY_DATABASE_URI'] = app.config['DATABASE_URL']
app.config['MENTION_LIMIT'] = MENTION_LIMIT
app.config['MULTIMEDIA_EMBEDDING_ENABLED'] = MULTIMEDIA_EMBEDDING_ENABLED
app.config['RESULTS_PER_PAGE_COMMENTS'] = RESULTS_PER_PAGE_COMMENTS
app.config['SCORE_HIDING_TIME_HOURS'] = SCORE_HIDING_TIME_HOURS
app.config['ENABLE_SERVICES'] = ENABLE_SERVICES

app.config['DBG_VOLUNTEER_PERMISSIVE'] = DBG_VOLUNTEER_PERMISSIVE
app.config['VOLUNTEER_JANITOR_ENABLE'] = VOLUNTEER_JANITOR_ENABLE

r=redis.Redis(host=environ.get("REDIS_URL", "redis://localhost"), decode_responses=True, ssl_cert_reqs=None)

def get_remote_addr():
	with app.app_context():
		return request.headers.get('X-Real-IP', default='127.0.0.1')

if not RATE_LIMITER_ENABLED:
	print("Rate limiter disabled in debug mode!")
limiter = flask_limiter.Limiter(
	key_func=get_remote_addr,
	app=app,
	default_limits=["3/second;30/minute;200/hour;1000/day"],
	application_limits=["10/second;200/minute;5000/hour;10000/day"],
	storage_uri=environ.get("REDIS_URL", "redis://localhost"),
	auto_check=False,
	enabled=RATE_LIMITER_ENABLED,
)

engine = create_engine(app.config['DATABASE_URL'])

db_session = scoped_session(sessionmaker(bind=engine, autoflush=False))
const_initialize(db_session)

cache = flask_caching.Cache(app)
flask_compress.Compress(app)
mail = flask_mail.Mail(app)

from files.routes.allroutes import *

if "load_chat" in argv:
	from files.routes.chat import *
else:
	from files.routes import *
