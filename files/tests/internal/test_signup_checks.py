'''Signup's anti-bot checks that only apply in some deployments, so the spec runs without them: an hCaptcha (when a site key is configured, read at startup) and a minimum time on the form (when the rate limiter is on).'''
import sys
import time

import pytest

import files.__main__ as main
import files.routes.login  # noqa: F401  (the module, not the route function of the same package name)
from files.helpers.captcha import HCAPTCHA_URL, validate_captcha
from files.tests.spec.harness import anon, assert_redirect, db, db_diff, external_web, factories, session
from files.tests.spec.harness.http import DEFAULT_USER_AGENT

login = sys.modules["files.routes.login"]


def test_without_a_site_key_any_answer_passes():
	assert validate_captcha("secret", "", "")


def test_without_an_answer_the_captcha_fails():
	assert not validate_captcha("secret", "sitekey", "")


@pytest.mark.parametrize("success", [True, False])
def test_the_answer_is_checked_with_hcaptcha(success):
	external_web.serve(HCAPTCHA_URL, method="POST", headers={"Content-Type": "application/json"}, body=f'{{"success": {str(success).lower()}}}')

	assert validate_captcha("secret", "sitekey", "answer") == success
	assert external_web.requests() == [("POST", HCAPTCHA_URL)]


def _signup(client, **fields):
	form = client.get("/signup")
	return client.post_raw("/signup", {"formkey": form.form_field("formkey"), "now": form.form_field("now"), "usernametwo": factories.unique("new"), "email": "", "password": factories.PASSWORD, "password_confirm": factories.PASSWORD, **fields})


def test_a_signup_failing_the_captcha_is_refused(monkeypatch):
	factories.user()
	monkeypatch.setattr(login, "HCAPTCHA_SITEKEY", "sitekey")
	external_web.serve(HCAPTCHA_URL, method="POST", headers={"Content-Type": "application/json"}, body='{"success": false}')

	with db_diff() as d:
		r = _signup(anon(), **{"h-captcha-response": "answer"})

	assert_redirect(r, "/signup", query_keys=("error",))
	d.assert_exactly()


def test_a_signup_sent_too_soon_after_the_form_is_refused(monkeypatch):
	factories.user()
	monkeypatch.setitem(main.app.config, "RATE_LIMITER_ENABLED", True)

	with db_diff() as d:
		r = _signup(anon())

	assert_redirect(r, "/signup", query_keys=("error",))
	d.assert_exactly()


def test_a_signup_sent_after_a_while_goes_through(monkeypatch):
	factories.user()
	monkeypatch.setitem(main.app.config, "RATE_LIMITER_ENABLED", True)
	client = anon()
	client.get("/signup")
	issued = int(time.time()) - 10
	username = factories.unique("new")

	r = client.post_raw("/signup", {"formkey": session.sign(f"signup+{issued}+{client.session()['signup_token']}+{DEFAULT_USER_AGENT}"), "now": issued, "usernametwo": username, "email": "", "password": factories.PASSWORD, "password_confirm": factories.PASSWORD})

	assert r.status == 302
	assert db.row("users", username=username)
