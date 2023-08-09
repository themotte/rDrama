'''
Main entry point for the application. Global state among other things are 
stored here.
'''

import gevent.monkey

gevent.monkey.patch_all()

# ^ special case: in general imports should go
# stdlib - externals - internals, but gevent does monkey patching for stdlib 
# functions so we want to monkey patch before importing other things

import faulthandler
from os import environ
from pathlib import Path

import flask
import flask_caching
import flask_compress
import flask_limiter
import flask_mail
import flask_profiler
import gevent
import redis
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from files.helpers.config.const import Service
from files.helpers.strings import bool_from_string

# first, let's parse arguments to find out what type of instance this is...

service:Service = Service.from_argv()

# ...and then let's create our flask app...

app = flask.app.Flask(__name__, template_folder='templates')
app.url_map.strict_slashes = False
app.jinja_env.cache = {}
app.jinja_env.auto_reload = True
faulthandler.enable()

# ...then check that debug mode was not accidentally enabled...

if bool_from_string(environ.get("ENFORCE_PRODUCTION", True)) and app.debug:
	raise ValueError("Debug mode is not allowed! If this is a dev environment, please set ENFORCE_PRODUCTION to false")

# ...and then attempt to load a .env file if the environment is not configured...

if environ.get("SITE_ID") is None:
	from dotenv import load_dotenv
	load_dotenv(dotenv_path=Path("bootstrap/site_env"))
	load_dotenv(dotenv_path=Path("env"), override=True)

# ...and let's add the flask profiler if it's enabled...

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

# ...and then let's set up the easy_profile analysis if it's enabled...

if bool_from_string(environ.get('DBG_SQL_ANALYSIS', False)):
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

# ...and let's load up app config...

from files.helpers.config.const import (DEFAULT_THEME, MAX_CONTENT_LENGTH,
                                        PERMANENT_SESSION_LIFETIME,
                                        SESSION_COOKIE_SAMESITE)
from files.helpers.config.environment import *

app.config.update({
	"SITE_ID": SITE_ID,
	"SITE_TITLE": SITE_TITLE,
	"SQLALCHEMY_TRACK_MODIFICATIONS": SQLALCHEMY_TRACK_MODIFICATIONS,
	"DATABASE_URL": DATABASE_URL,
	"SECRET_KEY": SECRET_KEY,
	"SERVER_NAME": SERVER_NAME,
	"SEND_FILE_MAX_AGE_DEFAULT": 0 if app.debug else 3153600,
	"SESSION_COOKIE_NAME": f'session_{SITE_ID.lower()}',
	"VERSION": "1.0.0",
	"MAX_CONTENT_LENGTH": MAX_CONTENT_LENGTH,
	"SESSION_COOKIE_SECURE": SESSION_COOKIE_SECURE,
	"SESSION_COOKIE_SAMESITE": SESSION_COOKIE_SAMESITE,
	"PERMANENT_SESSION_LIFETIME": PERMANENT_SESSION_LIFETIME,
	"DEFAULT_COLOR": DEFAULT_COLOR,
	"DEFAULT_THEME": DEFAULT_THEME,
	"FORCE_HTTPS": 1,
	"UserAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
	"HCAPTCHA_SITEKEY": HCAPTCHA_SITEKEY,
	"HCAPTCHA_SECRET": HCAPTCHA_SECRET,
	"SPAM_SIMILARITY_THRESHOLD": SPAM_SIMILARITY_THRESHOLD,
	"SPAM_URL_SIMILARITY_THRESHOLD": SPAM_URL_SIMILARITY_THRESHOLD,
	"SPAM_SIMILAR_COUNT_THRESHOLD": SPAM_SIMILAR_COUNT_THRESHOLD,
	"COMMENT_SPAM_SIMILAR_THRESHOLD": COMMENT_SPAM_SIMILAR_THRESHOLD,
	"COMMENT_SPAM_COUNT_THRESHOLD": COMMENT_SPAM_COUNT_THRESHOLD,
	"CACHE_TYPE": "RedisCache",
	"CACHE_REDIS_URL": CACHE_REDIS_URL,
	"MAIL_SERVER": MAIL_SERVER,
	"MAIL_PORT": MAIL_PORT,
	"MAIL_USE_TLS": MAIL_USE_TLS,
	"DESCRIPTION": DESCRIPTION,
	"MAIL_USERNAME": MAIL_USERNAME,
	"MAIL_PASSWORD": MAIL_PASSWORD,
	"DESCRIPTION": DESCRIPTION,
	"SETTINGS": {},
	"SQLALCHEMY_DATABASE_URI": DATABASE_URL,
	"MENTION_LIMIT": MENTION_LIMIT,
	"MULTIMEDIA_EMBEDDING_ENABLED": MULTIMEDIA_EMBEDDING_ENABLED,
	"RESULTS_PER_PAGE_COMMENTS": RESULTS_PER_PAGE_COMMENTS,
	"SCORE_HIDING_TIME_HOURS": SCORE_HIDING_TIME_HOURS,
	"ENABLE_SERVICES": ENABLE_SERVICES,
	"RATE_LIMITER_ENABLED": RATE_LIMITER_ENABLED,

	"DBG_VOLUNTEER_PERMISSIVE": DBG_VOLUNTEER_PERMISSIVE,
	"VOLUNTEER_JANITOR_ENABLE": VOLUNTEER_JANITOR_ENABLE,
})

# ...and then let's load redis so that...

r = redis.Redis(
	host=CACHE_REDIS_URL, 
	decode_responses=True, 
	ssl_cert_reqs=None
)

# ...we can configure our ratelimiter...

def get_remote_addr():
	with app.app_context():
		return request.headers.get('X-Real-IP', default='127.0.0.1')

if service.enable_services and not RATE_LIMITER_ENABLED:
	print("Rate limiter disabled in debug mode!")

limiter = flask_limiter.Limiter(
	key_func=get_remote_addr,
	app=app,
	default_limits=["3/second;30/minute;200/hour;1000/day"],
	application_limits=["10/second;200/minute;5000/hour;10000/day"],
	storage_uri=CACHE_REDIS_URL,
	auto_check=False,
	enabled=RATE_LIMITER_ENABLED,
)

# ...and then after that we can load the database.

engine: Engine = create_engine(DATABASE_URL)
db_session_factory: sessionmaker = sessionmaker(
	bind=engine,
	autoflush=False,
	future=True,
)
db_session: scoped_session = scoped_session(db_session_factory)

# now that we've that, let's add the cache, compression, and mail extensions to our app...

cache = flask_caching.Cache(app)
flask_compress.Compress(app)
mail = flask_mail.Mail(app)

# ...and then import the before and after request handlers if this we will import routes.

if service.enable_services:
	from files.routes.allroutes import *

# setup is done. let's conditionally import the rest of the routes.

if service == Service.THEMOTTE:
	from files.routes import *
elif service == Service.CHAT:
	from files.routes.chat import *
