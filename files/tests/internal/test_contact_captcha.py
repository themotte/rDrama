'''The contact form's hCaptcha for visitors, which applies only when a site key is configured (read at startup), so the spec runs without it.'''
import pytest

from files.helpers.captcha import HCAPTCHA_URL
from files.helpers.config import environment
from files.tests.spec.harness import anon, as_user, assert_html, assert_status, db_diff, external_web, factories

@pytest.fixture
def site_key(monkeypatch):
	monkeypatch.setattr(environment, "HCAPTCHA_SITEKEY", "sitekey")


def _answer(success: bool):
	external_web.serve(HCAPTCHA_URL, method="POST", headers={"Content-Type": "application/json"}, body=f'{{"success": {str(success).lower()}}}')


def test_a_visitor_failing_the_captcha_is_refused(site_key):
	_answer(False)

	with db_diff() as d:
		r = anon().post_raw("/send_admin", {"message": factories.unique(), "h-captcha-response": "answer"})

	assert_status(r, 403)
	d.assert_exactly()


def test_an_answer_hcaptcha_seems_to_pass_over_an_untrusted_connection_is_refused(site_key):
	external_web.serve(HCAPTCHA_URL, method="POST", headers={"Content-Type": "application/json"}, body='{"success": true}', trusted=False)

	r = anon().post_raw("/send_admin", {"message": factories.unique(), "h-captcha-response": "answer"})

	assert_status(r, 403)


def test_a_visitor_passing_the_captcha_is_heard(site_key):
	_answer(True)

	r = anon().post_raw("/send_admin", {"message": factories.unique(), "h-captcha-response": "answer"})

	assert_html(r, 200)


def test_members_arent_asked(site_key):
	r = as_user(factories.user()).post("/send_admin", {"message": factories.unique()})

	assert_html(r, 200)
	assert external_web.requests() == []
