'''
Every piece of deployment configuration the harness shares with the app under test. Both read the same environment, so this list is also the configuration contract a reimplementation must honor.
'''
import os


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
	'''The SMTP server the app sends mail through (port 587, STARTTLS when credentials are configured).'''
	return os.environ["MAIL_SERVER"]


def site_settings_path() -> str:
	'''A JSON file of runtime-toggleable settings. The app must re-read it on every request, because admins change it while the site runs and side-by-side deployments share it.'''
	return os.environ["SITE_SETTINGS_PATH"]


# Tuning values the spec runs at. The tests read them here rather than assuming them.

def comments_per_page() -> int:
	'''RESULTS_PER_PAGE_COMMENTS: a post page, and each /viewmore page, holds whole top-level threads until it has this many comments or more.'''
	return int(os.environ["RESULTS_PER_PAGE_COMMENTS"])


def score_hiding_hours() -> int:
	'''SCORE_HIDING_TIME_HOURS: scores are hidden while an item is younger than this.'''
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
