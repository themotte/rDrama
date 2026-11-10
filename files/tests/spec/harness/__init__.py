'''
The spec tier's whole vocabulary. Spec tests import from here and nowhere in `files` outside this package.
'''
import json
import re
import time
from datetime import datetime, timezone
from typing import NamedTuple

from files.tests.spec.harness import backend, config, db, external_web, factories, markup, seed, session, uploads
from files.tests.spec.harness.asserts import *
from files.tests.spec.harness.asserts import __all__ as _asserts_all
from files.tests.spec.harness.db import ANY, between, db_diff
from files.tests.spec.harness.http import Client, Response
from files.tests.spec.harness.markup import element_html, element_text, element_values, has_element, images_in, input_names, links, notification_counts, page_title

__all__ = ["config", "db", "external_web", "factories", "seed", "session", "uploads", "XHR", "can_log_in", "markup", "notification_counts", "element_text", "element_html", "has_element", "element_values", "links", "input_names", "images_in", "page_title", "urls_in", "totp_step_settle", "ANY", "between", "db_diff", "Client", "Response", "anon", "as_user", "as_api", "site_settings_set", "run_background_work", "run_scheduler", "utc_now_naive", "sent_mail", "cli", "CliResult", "assert_cli_ok", *_asserts_all]


XHR = {"xhr": "1"}
'''Headers marking a script request: errors come back as JSON instead of pages or login redirects.'''


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
	Does one pass of the scheduled-task worker (the `cron` command) at `at` (an aware datetime): recovering any task left running (see spec/scheduler/test_runs.py), then running every task due at `at`.

	The worker's clock reads `at` throughout, so `at` is: when the tasks run (`tasks_repeatable.run_time_last`), the start and completion times of their runs, and a scheduled post's `created_utc` and the dates in its title. Everything else the run writes (votes, notifications) takes the real time.

	A backend driving the site out of process would need a test-mode way to run one pass on a given clock, such as a test-only `cron --once --now=<epoch>`.
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
