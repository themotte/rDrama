'''
The signed links and form tokens of password reset, 2FA login and 2FA removal: the site issues them in the formats documented in harness/session.py, accepts them while fresh, and refuses them when dated in the future or when the token isn't ASCII.
'''
import time
from urllib.parse import parse_qs, urlsplit

import pyotp

from files.tests.spec.harness import *


def _link_params(mail, path):
	[link] = {url for url in urls_in(mail["body"]) if urlsplit(url).path == path}
	return {k: v[0] for k, v in parse_qs(urlsplit(link).query).items()}


def _reset_link(u, issued):
	return {"id": u["id"], "time": issued, "token": session.sign(f"forgot+{u['id']}+{issued}+{u['login_nonce']}")}


def _reset_form(u, issued, password):
	return {"user_id": u["id"], "time": issued, "token": session.sign(f"reset+{u['id']}+{issued}+{u['login_nonce']}"), "password": password, "confirm_password": password}


def _removal_link(u, issued):
	return {"id": u["id"], "t": issued, "token": session.sign(f"2fa-remove+{u['id']}+{u['username']}+{issued}+{u['mfa_secret']}+{u['login_nonce']}")}


# Password reset

def test_the_reset_mail_links_to_a_signed_reset_page():
	u = factories.user(email=f"{factories.unique()}@example.com")

	anon().post("/forgot", {"username": u["username"], "email": u["email"]})

	params = _link_params(sent_mail()[0], "/reset")
	assert params["token"] == session.sign(f"forgot+{u['id']}+{params['time']}+{u['login_nonce']}")


def test_a_reset_link_opens_a_form_carrying_the_signed_reset_token():
	u = factories.user()
	issued = int(time.time())

	r = anon().get("/reset", params=_reset_link(u, issued))

	assert_html(r, 200)
	assert r.form_field("token") == session.sign(f"reset+{u['id']}+{issued}+{u['login_nonce']}")


def test_a_reset_link_dated_in_the_future_opens_no_form():
	u = factories.user()

	r = anon().get("/reset", params=_reset_link(u, int(time.time()) + 3600))

	assert_html(r, 200)
	assert r.form_field("token") is None


def test_a_reset_link_with_a_token_that_is_not_ascii_is_refused():
	u = factories.user()

	r = anon().get("/reset", params={**_reset_link(u, int(time.time())), "token": "é" * 32})

	assert_status(r, 400)


def test_the_reset_form_sets_the_password():
	u = factories.user()
	new_password = f"new {factories.unique()} password"

	r = anon().post_raw("/reset", _reset_form(u, int(time.time()), new_password))

	assert_html(r, 200)
	assert can_log_in(u, new_password)


def test_a_reset_form_dated_in_the_future_sets_nothing():
	u = factories.user()

	with db_diff() as d:
		r = anon().post_raw("/reset", _reset_form(u, int(time.time()) + 3600, f"new {factories.unique()} password"))

	assert_html(r, 200)
	d.assert_exactly()


# 2FA login

def _two_factor_user():
	return factories.user(mfa_secret=pyotp.random_base32())


def test_the_2fa_challenge_is_signed():
	u = _two_factor_user()

	r = anon().post_raw("/login", {"username": u["username"], "password": factories.PASSWORD})

	assert_html(r, 200)
	assert r.form_field("hash") == session.sign(f"2fa-challenge+{u['id']}+{r.form_field('time')}+{u['login_nonce']}")


def test_a_signed_challenge_and_the_current_code_log_in():
	u = _two_factor_user()
	issued = int(time.time())
	client = anon()
	totp_step_settle()

	r = client.post_raw("/login", {"username": u["username"], "time": issued, "hash": session.sign(f"2fa-challenge+{u['id']}+{issued}+{u['login_nonce']}"), "2fa_token": pyotp.TOTP(u["mfa_secret"]).now()})

	assert_redirect(r, "/")
	assert client.user_id == u["id"]


def test_a_challenge_dated_in_the_future_goes_back_to_login():
	u = _two_factor_user()
	issued = int(time.time()) + 3600
	client = anon()
	totp_step_settle()

	r = client.post_raw("/login", {"username": u["username"], "time": issued, "hash": session.sign(f"2fa-challenge+{u['id']}+{issued}+{u['login_nonce']}"), "2fa_token": pyotp.TOTP(u["mfa_secret"]).now()})

	assert_redirect(r, "/login")
	assert client.user_id is None


# 2FA removal

def test_the_removal_mail_links_to_a_signed_removal():
	u = factories.user(email=f"{factories.unique()}@example.com", mfa_secret=pyotp.random_base32())

	anon().post("/request_2fa_disable", {"username": u["username"], "password": factories.PASSWORD, "email": u["email"]})

	params = _link_params(sent_mail()[0], "/reset_2fa")
	assert params["token"] == session.sign(f"2fa-remove+{u['id']}+{u['username']}+{params['t']}+{u['mfa_secret']}+{u['login_nonce']}")


def test_a_removal_link_asks_before_removing_2fa():
	u = _two_factor_user()
	link = _removal_link(u, int(time.time()) - 72 * 3600)

	with db_diff() as d:
		r = anon().get("/reset_2fa", params=link)

	assert_html(r, 200)
	assert (r.form_field("id"), r.form_field("t"), r.form_field("token")) == (str(link["id"]), str(link["t"]), link["token"])
	d.assert_exactly()


def test_confirming_a_removal_link_removes_2fa():
	u = _two_factor_user()

	with db_diff() as d:
		r = anon().post_raw("/reset_2fa", _removal_link(u, int(time.time()) - 72 * 3600))

	assert_html(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {"mfa_secret": None}}})


def test_a_removal_link_dated_in_the_future_removes_nothing():
	u = _two_factor_user()

	with db_diff() as d:
		r = anon().post_raw("/reset_2fa", _removal_link(u, int(time.time()) + 3600))

	assert_html(r, 200)
	d.assert_exactly()


# Email verification

def test_a_verification_link_with_a_token_that_is_not_ascii_is_refused():
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).get("/activate", params={"email": "a@example.com", "id": u["id"], "time": int(time.time()), "token": "é" * 32})

	assert_status(r, 403)
	d.assert_exactly()


# Form key

def test_a_form_key_that_is_not_ascii_counts_as_no_form_key():
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.post_raw("/settings/profile", {"cardview": "true", "formkey": "é" * 32}, headers=XHR)

	assert_api_unauthorized(r)
	d.assert_exactly()


def test_a_form_key_that_is_not_a_string_counts_as_no_form_key():
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.post_json("/settings/profile", {"cardview": True, "formkey": 1}, headers=XHR)

	assert_api_unauthorized(r)
	d.assert_exactly()
