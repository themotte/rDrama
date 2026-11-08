'''
The spec tier's whole vocabulary. Spec tests import from here and nowhere in `files` outside this package.
'''
import json
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import NamedTuple

from files.tests.spec.harness import backend, config, db, external_web, factories, seed, session, uploads
from files.tests.spec.harness.asserts import *
from files.tests.spec.harness.asserts import __all__ as _asserts_all
from files.tests.spec.harness.db import ANY, between, db_diff
from files.tests.spec.harness.http import Client, Response

__all__ = ["config", "db", "external_web", "factories", "seed", "session", "uploads", "XHR", "TOR", "can_log_in", "notification_counts", "element_text", "urls_in", "totp_step_settle", "ANY", "between", "db_diff", "Client", "Response", "anon", "as_user", "as_api", "site_settings_set", "run_background_work", "run_scheduler", "utc_now_naive", "sent_mail", "cli", "CliResult", "assert_cli_ok", *_asserts_all]


XHR = {"xhr": "1"}
'''Headers marking a script request: errors come back as JSON instead of pages or login redirects.'''
TOR = {"cf-ipcountry": "T1"}
'''Headers marking a request as arriving through Tor (as reported by the CDN in front of the site).'''


def anon() -> Client:
	return Client()


def as_user(user: dict) -> Client:
	return Client().login_as(user)


def as_api(token: str) -> Client:
	'''A client of the API: authenticates every request with an access token (see factories.api_token) instead of a session, and sends no form key.'''
	return Client(authorization=token)


def site_settings_set(key, value):
	'''Changes one entry of the site settings file, which the app must re-read on every request (see config.site_settings_path).'''
	path = config.site_settings_path()
	with open(path) as f:
		settings = json.load(f)
	settings[key] = value
	with open(path, "w") as f:
		json.dump(settings, f)


def run_background_work():
	'''Runs work the app handed off to the background (thumbnail fetching) to completion.'''
	backend.run_background_work()


def utc_now_naive() -> datetime:
	'''The current time as the database's timestamp columns hold times: UTC, without a zone.'''
	return datetime.now(timezone.utc).replace(tzinfo=None)


def run_scheduler(at: datetime):
	'''
	Does what the scheduled-task worker (the `cron` command) does when it starts at `at` (an aware datetime), up to the end of its first pass over the tasks: recovering tasks a stopped worker left running, then running every task due at `at`.

	The worker's clock reads `at` throughout, so `at` is: when the tasks run (`tasks_repeatable.run_time_last`), the start and completion times of their runs, and a scheduled post's `created_utc` and the dates in its title. Everything else the run writes (votes, notifications) takes the real time.

	A backend driving the site out of process would need a test-mode way to start the worker on a given clock, such as a test-only `cron --once --now=<epoch>`.
	'''
	backend.run_scheduler(at)


class CliResult(NamedTuple):
	exit_code: int
	output: str


def cli(*args: str) -> CliResult:
	'''Runs one of the site's command-line commands (the first argument names it; the names are contract) against the same database and cache, and returns its exit code and output.'''
	return CliResult(*backend.cli(args))


def assert_cli_ok(result: CliResult):
	assert result.exit_code == 0, f"command exited {result.exit_code}: {result.output}"


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


def notification_counts(r: Response) -> dict:
	'''
	The unread counts a page shows its logged-in viewer:
	- "bell": the header's notification count;
	- "bell_link": where the bell leads;
	- "all" and "posts": the notification pages' tab counts, None on other pages.

	They're read from the page's `data-notification-count` (on the bell's link) and `data-tab-count` (on the tab links of /notifications and /notifications/posts) attributes, part of the pages' markup contract.
	'''
	found = {"bell": None, "bell_link": None, "all": None, "posts": None}

	class Parser(HTMLParser):
		def handle_starttag(self, tag, attrs):
			attrs = dict(attrs)
			if "data-notification-count" in attrs:
				count, link = int(attrs["data-notification-count"]), attrs["href"]
				assert found["bell"] in (None, count) and found["bell_link"] in (None, link), "the header's bells disagree"
				found["bell"], found["bell_link"] = count, link
			if "data-tab-count" in attrs:
				found[{"/notifications": "all", "/notifications/posts": "posts"}[attrs["href"]]] = int(attrs["data-tab-count"])

	Parser().feed(r.text)
	assert found["bell"] is not None, "the page has no notification bell"
	return found


_VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


def element_text(r: Response, element_id: str) -> str:
	'''The text a reader sees inside the page's element with the id `element_id` (ids such as "post-<id>" and "comment-<id>" are part of the page contract), with runs of whitespace made one space.'''
	found = {"depth": 0, "seen": False, "text": []}

	class Parser(HTMLParser):
		def handle_starttag(self, tag, attrs):
			if found["depth"]:
				if tag not in _VOID_TAGS: found["depth"] += 1
			elif dict(attrs).get("id") == element_id and not found["seen"]:
				found["seen"] = True
				found["depth"] = 0 if tag in _VOID_TAGS else 1

		def handle_endtag(self, tag):
			if found["depth"] and tag not in _VOID_TAGS: found["depth"] -= 1

		def handle_data(self, data):
			if found["depth"]: found["text"].append(data)

	Parser().feed(r.text)
	assert found["seen"], f"the page has no element with id {element_id!r}"
	return " ".join("".join(found["text"]).split())
