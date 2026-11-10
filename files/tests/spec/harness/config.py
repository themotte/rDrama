'''
The deployment configuration a reimplementation must honor: every environment variable it reads (ENVIRONMENT), and the pieces of it the harness shares with the app under test. Both read the same environment. The current implementation also reads variables of its own, for its tests, its developers and its start-up; those aren't listed.
'''
import enum
import os


class Env(enum.Enum):
	DEPLOYMENT = "deployment"
	'''Describes the deployment; a reimplementation reads it with the same meaning.'''
	TUNING = "tuning"
	'''A size, threshold or default; a reimplementation reads it with the same meaning. The spec runs at the configured value, and the tests that depend on one read it through the accessors below. The similarity thresholds have none: the spam tests' texts are chosen for values near production's.'''
	PRECONDITION = "precondition"
	'''A switch the spec needs at one value (PRECONDITIONS); a reimplementation reads it with the same meaning.'''


ENVIRONMENT = {
	"DOMAIN": Env.DEPLOYMENT,
	"SITE_ID": Env.DEPLOYMENT,
	"SITE_TITLE": Env.DEPLOYMENT,
	"DESCRIPTION": Env.DEPLOYMENT,
	"MASTER_KEY": Env.DEPLOYMENT,
	"DATABASE_URL": Env.DEPLOYMENT,
	"REDIS_URL": Env.DEPLOYMENT,
	"SITE_SETTINGS_PATH": Env.DEPLOYMENT,
	"IMAGES_DIR": Env.DEPLOYMENT,
	"MAIL_SERVER": Env.DEPLOYMENT,
	"MAIL_USERNAME": Env.DEPLOYMENT,
	"MAIL_PASSWORD": Env.DEPLOYMENT,
	"HCAPTCHA_SECRET": Env.DEPLOYMENT,
	"DEFAULT_COLOR": Env.TUNING,
	"CARD_VIEW": Env.TUNING,
	"MENTION_LIMIT": Env.TUNING,
	"RESULTS_PER_PAGE_COMMENTS": Env.TUNING,
	"SCORE_HIDING_TIME_HOURS": Env.TUNING,
	"SPAM_SIMILARITY_THRESHOLD": Env.TUNING,
	"SPAM_URL_SIMILARITY_THRESHOLD": Env.TUNING,
	"SPAM_SIMILAR_COUNT_THRESHOLD": Env.TUNING,
	"COMMENT_SPAM_SIMILAR_THRESHOLD": Env.TUNING,
	"COMMENT_SPAM_COUNT_THRESHOLD": Env.TUNING,
	"HCAPTCHA_SITEKEY": Env.PRECONDITION,
	"VOLUNTEER_JANITOR_ENABLE": Env.PRECONDITION,
}

PRECONDITIONS = {
	"HCAPTCHA_SITEKEY": "",
	"VOLUNTEER_JANITOR_ENABLE": True,
}
'''The values the spec needs; an absent variable counts as its default here (no site key: no captcha; the volunteer janitor on).'''


def site_host() -> str:
	return os.environ["DOMAIN"].strip()


def site_url() -> str:
	'''The site's own absolute URL: plain http for a host containing "localhost", https otherwise.'''
	return ("http://" if "localhost" in site_host() else "https://") + site_host()


def site_id() -> str:
	return os.environ["SITE_ID"].strip()


def master_key() -> str:
	return os.environ["MASTER_KEY"]


def images_dir() -> str:
	'''The upload store: a flat directory whose files the app serves at /images/<filename>. Wiped between tests.'''
	return os.environ["IMAGES_DIR"]


def mail_server() -> str:
	'''The SMTP server the app sends mail through (port 587, STARTTLS).'''
	return os.environ["MAIL_SERVER"]


def site_settings_path() -> str:
	'''A JSON file of runtime-toggleable settings. The app must re-read it on every request, because admins change it while the site runs, and replace it whole when changing it. Side-by-side deployments must share it.'''
	return os.environ["SITE_SETTINGS_PATH"]


# Tuning values the spec runs at. The tests read them here rather than assuming them.

def comments_per_page() -> int:
	'''RESULTS_PER_PAGE_COMMENTS: a post page, and each /viewmore page, holds whole top-level threads until it has this many comments or more.'''
	return int(os.environ["RESULTS_PER_PAGE_COMMENTS"])


def score_hiding_hours() -> int:
	'''SCORE_HIDING_TIME_HOURS: scores are hidden while an item is younger than this. The spec needs at least 1.'''
	return int(os.environ["SCORE_HIDING_TIME_HOURS"])


def mention_limit() -> int:
	'''MENTION_LIMIT: the most existing users a text may mention.'''
	return int(os.environ["MENTION_LIMIT"])


def post_spam_count() -> int:
	'''SPAM_SIMILAR_COUNT_THRESHOLD: how many similar recent posts make a new one spam, before the account-age multipliers.'''
	return int(os.environ["SPAM_SIMILAR_COUNT_THRESHOLD"])


def comment_spam_count() -> int:
	'''COMMENT_SPAM_COUNT_THRESHOLD: how many similar recent comments a new comment or an edit may have before it is refused, before the account-age multipliers.'''
	return int(os.environ["COMMENT_SPAM_COUNT_THRESHOLD"])


def default_color() -> str:
	'''DEFAULT_COLOR: the colour (3 or 6 hex digits, no "#") a new account's name, title and theme start with.'''
	return os.environ["DEFAULT_COLOR"].strip()


def card_view_default() -> bool:
	'''CARD_VIEW: whether new accounts, and visitors, get listings as cards.'''
	return os.environ["CARD_VIEW"].strip().lower() in ("yes", "true", "t", "on", "1")
