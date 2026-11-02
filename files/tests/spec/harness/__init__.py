'''
The spec tier's whole vocabulary. Spec tests import from here and nowhere in `files` outside this package.
'''
import json
import re
import time

from files.tests.spec.harness import backend, config, db, factories, seed, session, uploads
from files.tests.spec.harness.asserts import *
from files.tests.spec.harness.asserts import __all__ as _asserts_all
from files.tests.spec.harness.db import ANY, db_diff
from files.tests.spec.harness.http import Client, Response

__all__ = ["config", "db", "factories", "seed", "session", "uploads", "XHR", "TOR", "can_log_in", "urls_in", "totp_step_settle", "ANY", "db_diff", "Client", "Response", "anon", "as_user", "site_settings_set", "run_background_work", "sent_mail", *_asserts_all]


XHR = {"xhr": "1"}
'''Headers marking a script request: errors come back as JSON instead of pages or login redirects.'''
TOR = {"cf-ipcountry": "T1"}
'''Headers marking a request as arriving through Tor (as reported by the CDN in front of the site).'''


def anon() -> Client:
	return Client()


def as_user(user: dict) -> Client:
	return Client().login_as(user)


def site_settings_set(key, value):
	'''Changes one entry of the site settings file, which the app must re-read on every request (see config.site_settings_path).'''
	path = config.site_settings_path()
	with open(path) as f:
		settings = json.load(f)
	settings[key] = value
	with open(path, "w") as f:
		json.dump(settings, f)


def run_background_work():
	'''Runs work the app handed off to the background (thumbnail fetching, push notifications) to completion.'''
	backend.run_background_work()


def sent_mail() -> list[dict]:
	'''
	Mail the app sent since the test began, oldest first, as dicts of "from" (envelope sender), "to" (list), "subject", "headers" (the parsed message) and "body" (all text parts, decoded, joined). See config.mail_server.
	'''
	mails = []
	for m in backend.sent_mail():
		message = m["message"]
		parts = [p.get_payload(decode=True).decode(p.get_content_charset() or "utf-8") for p in message.walk() if p.get_content_maintype() == "text"]
		mails.append({"from": m["from"], "to": m["to"], "subject": message["Subject"], "headers": message, "body": "\n".join(parts)})
	return mails


def urls_in(text: str) -> list[str]:
	'''Absolute URLs in `text`, with HTML entity escaping undone.'''
	return [u.replace("&amp;", "&") for u in re.findall(r'https?://[^\s"<>\']+', text)]


def totp_step_settle():
	'''Waits out the last moments of the current 30-second TOTP step, so a code generated now is checked within the same step.'''
	remaining = 30 - time.time() % 30
	if remaining < 3:
		time.sleep(remaining + 0.1)


def can_log_in(user: dict, password: str) -> bool:
	client = anon()
	client.post_raw("/login", {"username": user["username"], "password": password})
	return client.user_id == user["id"]
