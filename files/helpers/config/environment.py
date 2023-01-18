from os import environ

from files.helpers.strings import bool_from_string

SITE = environ.get("DOMAIN", '').strip()
SITE_ID = environ.get("SITE_ID").strip()
SITE_TITLE = environ.get("SITE_TITLE").strip()
SCHEME = environ.get('SCHEME', 'http' if 'localhost' in SITE else 'https')

if "localhost" in SITE: 
	SITE_FULL = 'http://' + SITE
else: 
	SITE_FULL = 'https://' + SITE

WELCOME_MSG = f"""Welcome to {SITE_TITLE}! Please read [the rules](/rules) first. Then [read some of our current conversations](/) and feel free to comment or post!
               We encourage people to comment even if they aren't sure they fit in; as long as your comment follows [community rules](/rules), we are happy to have 
			   posters from all backgrounds, education levels, and specialties.
			   """

SQLALCHEMY_TRACK_MODIFICATIONS = False
DATABASE_URL = environ.get("DATABASE_URL", "postgresql://postgres@localhost:5432")
SECRET_KEY = environ.get('MASTER_KEY', '')
SERVER_NAME = environ.get("DOMAIN").strip()
SESSION_COOKIE_SECURE = "localhost" not in SERVER_NAME
DEFAULT_COLOR = environ.get("DEFAULT_COLOR", "fff").strip()
HCAPTCHA_SITEKEY = environ.get("HCAPTCHA_SITEKEY","").strip()
HCAPTCHA_SECRET = environ.get("HCAPTCHA_SECRET","").strip()

if not SECRET_KEY:
	raise Exception("Secret key not set!")

# spam filter

SPAM_SIMILARITY_THRESHOLD = float(environ.get("SPAM_SIMILARITY_THRESHOLD", 0.5))
''' Spam filter similarity threshold (posts) '''
SPAM_URL_SIMILARITY_THRESHOLD = float(environ.get("SPAM_URL_SIMILARITY_THRESHOLD", 0.1))
''' Spam filter similarity threshold for URLs (posts) '''
SPAM_SIMILAR_COUNT_THRESHOLD = int(environ.get("SPAM_SIMILAR_COUNT_THRESHOLD", 10))
''' Spam filter similarity count (posts) '''
COMMENT_SPAM_SIMILAR_THRESHOLD = float(environ.get("COMMENT_SPAM_SIMILAR_THRESHOLD", 0.5))
''' Spam filter similarity threshold (comments)'''
COMMENT_SPAM_COUNT_THRESHOLD = int(environ.get("COMMENT_SPAM_COUNT_THRESHOLD", 10))
''' Spam filter similarity count (comments) '''


CACHE_REDIS_URL = environ.get("REDIS_URL", "redis://localhost")
MAIL_SERVER = environ.get("MAIL_SERVER", "").strip()
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = environ.get("MAIL_USERNAME", "").strip()
MAIL_PASSWORD = environ.get("MAIL_PASSWORD", "").strip()
DESCRIPTION = environ.get("DESCRIPTION", "DESCRIPTION GOES HERE").strip()
SQLALCHEMY_DATABASE_URI = DATABASE_URL

MENTION_LIMIT = int(environ.get('MENTION_LIMIT', 100))
''' Maximum amount of username mentions '''

MULTIMEDIA_EMBEDDING_ENABLED = bool_from_string(environ.get('MULTIMEDIA_EMBEDDING_ENABLED', False))
''' 
Whether multimedia will be embedded into a page. Note that this does not 
affect posts or comments retroactively.
'''

RESULTS_PER_PAGE_COMMENTS = int(environ.get('RESULTS_PER_PAGE_COMMENTS', 50))
SCORE_HIDING_TIME_HOURS = int(environ.get('SCORE_HIDING_TIME_HOURS', 0))


ENABLE_SERVICES = bool_from_string(environ.get('ENABLE_SERVICES', False))
'''
Whether to start up scheduled tasks. Usually `True` when running as an app and
`False` when running as a script (for example to perform migrations).

See https://github.com/themotte/rDrama/pull/427 for more info.
'''

DBG_VOLUNTEER_PERMISSIVE = bool_from_string(environ.get('DBG_VOLUNTEER_PERMISSIVE', False))
VOLUNTEER_JANITOR_ENABLE = bool_from_string(environ.get('VOLUNTEER_JANITOR_ENABLE', True))

RATE_LIMITER_ENABLED = not bool_from_string(environ.get('DBG_LIMITER_DISABLED', False))

# other stuff from const.py that aren't constants
dues = int(environ.get("DUES").strip())

IMGUR_KEY = environ.get("IMGUR_KEY", "").strip()
PUSHER_ID = environ.get("PUSHER_ID", "").strip()
PUSHER_KEY = environ.get("PUSHER_KEY", "").strip()

YOUTUBE_KEY = environ.get("YOUTUBE_KEY", "").strip()

CF_KEY = environ.get("CF_KEY", "").strip()
CF_ZONE = environ.get("CF_ZONE", "").strip()
CF_HEADERS = {"Authorization": f"Bearer {CF_KEY}", "Content-Type": "application/json"}
