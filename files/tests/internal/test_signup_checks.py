'''Signup's hCaptcha, which only applies where a site key is configured (read at startup), so the spec runs without it. Its minimum time on the form is in spec/limits.'''
import pytest

from files.helpers.captcha import HCAPTCHA_URL, validate_captcha
from files.helpers.config import environment
from files.tests.spec.harness import anon, assert_redirect, db_diff, external_web, factories


@pytest.fixture
def site_key(monkeypatch):
	monkeypatch.setattr(environment, "HCAPTCHA_SITEKEY", "sitekey")
	monkeypatch.setattr(environment, "HCAPTCHA_SECRET", "secret")


def test_without_a_site_key_any_answer_passes(monkeypatch):
	monkeypatch.setattr(environment, "HCAPTCHA_SITEKEY", "")
	assert validate_captcha("")


def test_without_an_answer_the_captcha_fails(site_key):
	assert not validate_captcha("")


@pytest.mark.parametrize("success", [True, False])
def test_the_answer_is_checked_with_hcaptcha(success, site_key):
	external_web.serve(HCAPTCHA_URL, method="POST", headers={"Content-Type": "application/json"}, body=f'{{"success": {str(success).lower()}}}')

	assert validate_captcha("answer") == success
	assert external_web.requests() == [("POST", HCAPTCHA_URL)]


def _signup(client, **fields):
	form = client.get("/signup")
	return client.post_raw("/signup", {"formkey": form.form_field("formkey"), "now": form.form_field("now"), "usernametwo": factories.unique("new"), "email": "", "password": factories.PASSWORD, "password_confirm": factories.PASSWORD, **fields})


def test_a_signup_failing_the_captcha_is_refused(site_key):
	factories.user()
	external_web.serve(HCAPTCHA_URL, method="POST", headers={"Content-Type": "application/json"}, body='{"success": false}')

	with db_diff() as d:
		r = _signup(anon(), **{"h-captcha-response": "answer"})

	assert_redirect(r, "/signup", query_keys=("error",))
	d.assert_exactly()


@pytest.mark.parametrize("failure", ["unreachable", "not json", "no verdict"])
def test_a_failing_captcha_service_fails_the_captcha(failure, capsys, site_key):
	if failure == "unreachable":
		external_web.unreachable(HCAPTCHA_URL, method="POST")
	else:
		external_web.serve(HCAPTCHA_URL, method="POST", headers={"Content-Type": "application/json"}, body={"not json": "<html>busy</html>", "no verdict": "{}"}[failure])

	assert validate_captcha("answer") is False
	assert "[captcha]" in capsys.readouterr().err


def test_a_signup_is_refused_while_the_captcha_service_is_down(site_key):
	factories.user()
	external_web.unreachable(HCAPTCHA_URL, method="POST")

	with db_diff() as d:
		r = _signup(anon(), **{"h-captcha-response": "answer"})

	assert_redirect(r, "/signup", query_keys=("error",))
	d.assert_exactly()
