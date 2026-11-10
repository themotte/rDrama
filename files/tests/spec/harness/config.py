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
