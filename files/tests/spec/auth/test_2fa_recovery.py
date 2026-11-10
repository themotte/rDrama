'''
Removing 2FA from an account whose codes are lost: GET /lost_2fa shows the request form; POST /request_2fa_disable with "username", "password" and "email" mails a removal link (format in harness/session.py) to the account's address when all three match an account with 2FA (the email ignoring case), and answers the same either way; the link (/reset_2fa?id=&t=&token=) shows a confirmation whose POST, carrying the same fields, removes 2FA. The link starts working 72 hours after it was sent, giving an owner who didn't ask for it time to change the password, which cancels it, and works for a day after that; both refuse a bad link the same way.
'''
import time

import pyotp
import pytest

from files.tests.spec.harness import *


def _member(**overrides):
	return factories.user(**{"email": f"{factories.unique()}@example.com", "mfa_secret": pyotp.random_base32(), **overrides})


def _request(u, **overrides):
	return anon().post("/request_2fa_disable", {"username": u["username"], "password": factories.PASSWORD, "email": u["email"], **overrides})


# How long a removal link waits before it works, and how long it works after that.
WAIT, WINDOW = 72 * 3600, 24 * 3600


def _follow(method, params):
	return anon().get("/reset_2fa", params=params) if method == "GET" else anon().post_raw("/reset_2fa", params)


BOTH = pytest.mark.parametrize("method", ["GET", "POST"])


def _link(u, issued, **overrides):
	return {"id": u["id"], "t": issued, "token": session.sign(f"2fa-remove+{u['id']}+{u['username']}+{issued}+{u['mfa_secret']}+{u['login_nonce']}"), **overrides}


def _title(r):
	'''The page's title, which tells answers apart where the rest of the page varies from request to request.'''
	return page_title(r)


def test_the_request_form():
	assert_html(anon().get("/lost_2fa"), 200)


def test_the_request_form_is_filled_in_for_a_logged_in_account():
	u = factories.user()

	r = as_user(u).get("/lost_2fa")

	assert_html(r, 200)
	assert (r.form_field("username"), r.form_field("email")) == (u["username"], "")


def test_a_matching_request_mails_the_account():
	u = _member()

	assert_html(_request(u), 200)

	[mail] = sent_mail()
	assert mail["to"] == [u["email"]]


@pytest.mark.parametrize("case", ["wrong password", "no 2FA", "no email", "unknown account"])
def test_other_requests_get_the_same_page_and_no_mail(case):
	u = _member(**{"no 2FA": {"mfa_secret": None}, "no email": {"email": None}}.get(case, {}))
	overrides = {"wrong password": {"password": "wrong " + factories.PASSWORD}, "no email": {"email": "a@example.com"}, "unknown account": {"username": factories.unique("nobody")}}.get(case, {})

	assert_html(_request(u, **overrides), 200)

	assert sent_mail() == []


def test_an_invalid_email_gets_no_mail():
	u = _member()

	assert_html(_request(u, email="not-an-email"), 200)

	assert sent_mail() == []


@BOTH
def test_an_expired_link_removes_nothing(method):
	u = _member()

	with db_diff() as d:
		r = _follow(method, _link(u, int(time.time()) - WAIT - WINDOW - 1))

	assert_html(r, 200)
	d.assert_exactly()


@BOTH
def test_a_link_with_a_bad_token_is_refused(method):
	u = _member()

	with db_diff() as d:
		r = _follow(method, _link(u, int(time.time()) - WAIT, token="0" * 32))

	assert_status(r, 403)
	d.assert_exactly()


@BOTH
def test_a_link_without_its_time_is_refused(method):
	u = _member()

	assert_status(_follow(method, {"id": u["id"], "token": "0" * 32}), 400)


@BOTH
def test_a_link_for_an_unknown_account_is_refused(method):
	u = _member()
	db.delete("users", id=u["id"])

	assert_status(_follow(method, _link(u, int(time.time()) - WAIT)), 404)


@BOTH
def test_a_link_for_an_account_without_2fa_is_refused(method):
	u = _member(mfa_secret=None)

	with db_diff() as d:
		r = _follow(method, _link(u, int(time.time()) - WAIT))

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("missing", ["email", "password"])
def test_a_request_missing_a_field_gets_no_mail(missing):
	u = _member()
	fields = {"username": u["username"], "password": factories.PASSWORD, "email": u["email"]}
	del fields[missing]

	assert_html(anon().post("/request_2fa_disable", fields), 200)

	assert sent_mail() == []


@BOTH
def test_a_link_with_a_malformed_time_is_refused(method):
	u = _member()

	assert_status(_follow(method, _link(u, int(time.time()) - WAIT, t="soon")), 400)


def test_a_request_naming_another_email_gets_no_mail():
	u = _member()

	assert_html(_request(u, email="someone.else@example.com"), 200)

	assert sent_mail() == []


def test_the_email_may_differ_in_case():
	u = _member()

	assert_html(_request(u, email=u["email"].upper()), 200)

	assert len(sent_mail()) == 1


def test_an_invalid_email_gets_the_same_answer_whether_or_not_the_account_exists():
	u = _member()

	answers = [_request(u, email="not-an-email"), _request(u, username=factories.unique("nobody"), email="not-an-email")]

	for r in answers:
		assert_html(r, 200)
	assert _title(answers[0]) == _title(answers[1])


@BOTH
def test_a_link_opened_before_its_wait_is_over_removes_nothing(method):
	u = _member()

	with db_diff() as d:
		r = _follow(method, _link(u, int(time.time()) - 3600))

	assert_html(r, 200)
	assert r.form_field("token") is None
	d.assert_exactly()


def test_changing_the_password_cancels_the_link():
	u = _member()
	link = _link(u, int(time.time()) - WAIT)
	as_user(u).post("/settings/security", {"old_password": factories.PASSWORD, "new_password": "new " + factories.PASSWORD, "cnf_password": "new " + factories.PASSWORD})

	with db_diff() as d:
		r = anon().post_raw("/reset_2fa", link)

	assert_status(r, 403)
	d.assert_exactly()


def test_the_mail_links_to_the_security_settings_in_full():
	u = _member()

	_request(u)

	assert f"{config.site_url()}/settings/security" in urls_in(sent_mail()[0]["body"])
