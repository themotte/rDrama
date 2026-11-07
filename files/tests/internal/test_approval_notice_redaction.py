'''
The migration that removes access tokens from the notices that approved API apps, run on notices as older versions wrote them. The suite's database is migrated empty, so its data step is checked here.
'''
import importlib.util
import pathlib
import secrets

from flask import g

from files.__main__ import app, db_session
from files.helpers.sanitize import sanitize
from files.tests.spec.harness import db, db_diff, factories, seed

_PATH = next(pathlib.Path(__file__).parents[3].glob("migrations/versions/*_redact_tokens_in_approval_notices.py"))


def _upgrade_sql():
	spec = importlib.util.spec_from_file_location("redaction_migration", _PATH)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module.UPGRADE_SQL


def _notice(text):
	with app.test_request_context("/"):
		g.db, g.v = db_session(), None
		body_html = sanitize(text)
	return factories.message(db.row("users", id=seed.SYSTEM_ID), None, body_html=body_html, distinguish_level=6)


def _token():
	return secrets.token_urlsafe(128)[:128]


def test_tokens_leave_approval_notices_and_nothing_else_changes():
	admin = factories.admin(3)
	tokens = [_token() for _ in range(3)]
	approvals = [
		_notice(f"@{admin['username']} has approved your application `{factories.unique('app')}`. Here's your access token: `{tokens[0]}`\nPlease check the guide [here](/api) if you don't know what to do next."),
		_notice(f"Your application `{factories.unique('app')}` has been approved. Here's your access token: `{tokens[1]}`\nPlease check the guide [here](/api) if you don't know what to do next."),
		_notice(f"@{admin['username']} has approved your application `{factories.unique('a`pp')}`. Here's your access token: `{tokens[2]}`\nPlease check the guide [here](/api) if you don't know what to do next."),
	]
	_notice(f"Your access token: `{factories.unique()}` is a fine thing to talk about")
	_notice(f"@{admin['username']} has rejected your application `{factories.unique('app')}`.")

	with db_diff() as d:
		db.execute(_upgrade_sql())

	redacted = {notice["id"]: db.row("comments", id=notice["id"])["body_html"] for notice in approvals}
	d.assert_exactly(updated={"comments": {notice_id: {"body_html": html} for notice_id, html in redacted.items()}})
	for token, html in zip(tokens, redacted.values()):
		assert token not in html and 'href="/settings/apps"' in html, html
