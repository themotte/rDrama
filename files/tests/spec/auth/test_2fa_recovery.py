'''
Removing 2FA from an account whose codes are lost: GET /lost_2fa shows the request form; POST /request_2fa_disable with "username", "password" and "email" mails a removal link (format in harness/session.py) to the account's address when all three match an account with 2FA (the email ignoring case), and answers the same either way; the link (/reset_2fa?id=&t=&token=) shows a confirmation whose POST, carrying the same fields, removes 2FA, for a day after the link was issued; both refuse a bad link the same way.
'''
import re
import time

import pyotp
import pytest

from files.tests.spec.harness import *


def _member(**overrides):
	return factories.user(**{"email": f"{factories.unique()}@example.com", "mfa_secret": pyotp.random_base32(), **overrides})


def _request(u, **overrides):
	return anon().post("/request_2fa_disable", {"username": u["username"], "password": factories.PASSWORD, "email": u["email"], **overrides})


def _follow(method, params):
	return anon().get("/reset_2fa", params=params) if method == "GET" else anon().post_raw("/reset_2fa", params)


BOTH = pytest.mark.parametrize("method", ["GET", "POST"])


def _link(u, issued, **overrides):
	return {"id": u["id"], "t": issued, "token": session.sign(f"2fa-remove+{u['id']}+{u['username']}+{issued}+{u['mfa_secret']}+{u['login_nonce']}"), **overrides}


def _title(r):
	'''The page's title, which tells answers apart where the rest of the page varies from request to request.'''
	return re.search(r"<title>(.*?)</title>", r.text, re.S).group(1)


def test_the_request_form():
	assert_html(anon().get("/lost_2fa"), 200)


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
		r = _follow(method, _link(u, int(time.time()) - 86401))

	assert_html(r, 200)
	d.assert_exactly()


@BOTH
def test_a_link_with_a_bad_token_is_refused(method):
	u = _member()

	with db_diff() as d:
		r = _follow(method, _link(u, int(time.time()), token="0" * 32))

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

	assert_status(_follow(method, _link(u, int(time.time()))), 404)


@BOTH
def test_a_link_for_an_account_without_2fa_is_refused(method):
	u = _member(mfa_secret=None)

	with db_diff() as d:
		r = _follow(method, _link(u, int(time.time())))

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

	assert_status(_follow(method, _link(u, int(time.time()), t="soon")), 400)


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