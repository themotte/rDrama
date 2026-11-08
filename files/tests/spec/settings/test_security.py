'''
GET /settings/security, POST /settings/security (password, email, two-factor) and POST /settings/log_out_all_others.

The page offers an account without two-factor login a fresh secret to set it up with, in the setup form's "2fa_secret" (a new one on every visit), beside the "2fa_token" field the authenticator's code goes in. An account that has two-factor login is offered no setup.

Changing the password and logging out other devices end the account's other sessions and every API token it holds (api/test_tokens).

/settings/security handles the first present form among new_password, new_email, 2fa_token, 2fa_remove. Each form re-checks the account password; rejections re-render the page with status 200 and change nothing.
'''
import re
import time
from urllib.parse import parse_qs, urlsplit

import pyotp
import pytest

from files.tests.spec.harness import *

NEW_PASSWORD = "a brand new password"

# Hashes written by any implementation must verify in every other one
PASSHASH_FORMAT = re.compile(r"^pbkdf2:sha512:\d+\$[^$]+\$[0-9a-f]{128}$")


def _security(user, data, headers=None):
	return as_user(user).post("/settings/security", data, headers=headers)


def test_the_page_offers_a_fresh_secret_to_set_up_two_factor_login():
	client = as_user(factories.user())

	first, second = client.get("/settings/security"), client.get("/settings/security")

	assert_html(first, 200)
	secrets = first.form_field("2fa_secret"), second.form_field("2fa_secret")
	assert all(re.fullmatch(r"[A-Z2-7]{32}", s) for s in secrets) and secrets[0] != secrets[1]
	assert first.form_field("2fa_token") is not None


def test_an_account_with_two_factor_login_is_offered_no_setup():
	r = as_user(factories.user(mfa_secret=pyotp.random_base32())).get("/settings/security")

	assert_html(r, 200)
	assert r.form_field("2fa_token") is None


def _wrong_token(secret):
	valid = {pyotp.TOTP(secret).at(time.time() + offset) for offset in (-30, 0, 30)}
	return next(t for t in ("000000", "111111", "222222", "333333") if t not in valid)


def test_request_without_a_recognized_form_is_rejected():
	u = factories.user()

	with db_diff() as d:
		r = _security(u, {}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


def test_password_form_takes_precedence_over_the_email_form():
	u = factories.user()

	with db_diff() as d:
		_security(u, {"old_password": factories.PASSWORD, "new_password": NEW_PASSWORD, "cnf_password": NEW_PASSWORD, "password": factories.PASSWORD, "new_email": "x@example.com"})

	d.assert_exactly(updated={"users": {u["id"]: {"passhash": ANY, "login_nonce": u["login_nonce"] + 1}}})
	assert sent_mail() == []


# Password

def test_password_change():
	u = factories.user()

	with db_diff() as d:
		r = _security(u, {"old_password": factories.PASSWORD, "new_password": NEW_PASSWORD, "cnf_password": NEW_PASSWORD})

	assert_html(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {"passhash": ANY, "login_nonce": u["login_nonce"] + 1}}})
	assert PASSHASH_FORMAT.match(db.row("users", id=u["id"])["passhash"])
	assert can_log_in(u, NEW_PASSWORD)
	assert not can_log_in(u, factories.PASSWORD)


def test_a_password_change_ends_the_accounts_api_tokens():
	u = factories.user()
	token = factories.api_token(u)
	application_id = db.row("client_auths", access_token=token)["oauth_client"]
	factories.authorization(factories.user(), db.row("oauth_apps", id=application_id))
	elsewhere = factories.oauth_app(factories.user())
	factories.authorization(u, elsewhere)

	with db_diff() as d:
		_security(u, {"old_password": factories.PASSWORD, "new_password": NEW_PASSWORD, "cnf_password": NEW_PASSWORD})

	d.assert_exactly(updated={"users": {u["id"]: {"passhash": ANY, "login_nonce": u["login_nonce"] + 1}}}, deleted={"client_auths": [(u["id"], application_id), (u["id"], elsewhere["id"])]})
	assert_api_unauthorized(as_api(token).get("/me"))


def test_password_change_keeps_the_session_that_made_it():
	u = factories.user()
	client = as_user(u)

	assert_html(client.post("/settings/security", {"old_password": factories.PASSWORD, "new_password": NEW_PASSWORD, "cnf_password": NEW_PASSWORD}), 200)

	assert_redirect(client.get("/me"), f"/@{u['username']}")


def test_password_change_ends_the_accounts_other_sessions():
	u = factories.user()
	elsewhere = as_user(u)

	assert_html(_security(u, {"old_password": factories.PASSWORD, "new_password": NEW_PASSWORD, "cnf_password": NEW_PASSWORD}), 200)

	assert_api_unauthorized(elsewhere.get("/me", headers=XHR))


def test_password_change_rejects_mismatched_confirmation():
	u = factories.user()

	with db_diff() as d:
		r = _security(u, {"old_password": factories.PASSWORD, "new_password": NEW_PASSWORD, "cnf_password": NEW_PASSWORD + "x"})

	assert_html(r, 200)
	d.assert_exactly()


def test_password_change_rejects_wrong_current_password():
	u = factories.user()

	with db_diff() as d:
		r = _security(u, {"old_password": "wrong", "new_password": NEW_PASSWORD, "cnf_password": NEW_PASSWORD})

	assert_html(r, 200)
	d.assert_exactly()


@pytest.mark.parametrize("bad", ["x" * 7, "x" * 101])
def test_password_must_be_8_to_100_characters(bad):
	u = factories.user()

	with db_diff() as d:
		r = _security(u, {"old_password": factories.PASSWORD, "new_password": bad, "cnf_password": bad})

	assert_html(r, 200)
	d.assert_exactly()


@pytest.mark.parametrize("good", ["x" * 8, "y" * 100])
def test_password_length_bounds_are_inclusive(good):
	u = factories.user()

	assert_html(_security(u, {"old_password": factories.PASSWORD, "new_password": good, "cnf_password": good}), 200)

	assert can_log_in(u, good)


# Email

def test_email_change_mails_a_verification_link_and_changes_nothing_yet():
	u = factories.user(email="old@example.com")
	new_email = f"{factories.unique()}@Example.com"

	with db_diff() as d:
		r = _security(u, {"password": factories.PASSWORD, "new_email": f"  {new_email} "})

	assert_html(r, 200)
	d.assert_exactly()
	[mail] = sent_mail()
	assert mail["to"] == [new_email.lower()]
	assert mail["from"] == f"{config.site_id()}@{config.site_host()}"
	[link] = {url for url in urls_in(mail["body"]) if urlsplit(url).path == "/activate"}
	params = {k: v[0] for k, v in parse_qs(urlsplit(link).query).items()}
	assert params["email"] == new_email.lower()
	assert params["id"] == str(u["id"])
	assert params["token"] == session.sign(f"activate+{params['email']}+{params['id']}+{params['time']}")


def test_following_the_email_change_link_sets_and_verifies_the_address():
	u = factories.user(email="old@example.com")
	new_email = f"{factories.unique()}@example.com"
	client = as_user(u)
	client.post("/settings/security", {"password": factories.PASSWORD, "new_email": new_email})
	[link] = {url for url in urls_in(sent_mail()[0]["body"]) if urlsplit(url).path == "/activate"}
	parts = urlsplit(link)

	with db_diff() as d:
		r = client.get(f"{parts.path}?{parts.query}")

	assert_html(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {"email": new_email, "is_activated": True}}})


@pytest.mark.parametrize("email", ["   ", "not-an-email", "a@b"])
def test_email_change_to_an_invalid_address_is_refused(email):
	u = factories.user()

	assert_html(_security(u, {"password": factories.PASSWORD, "new_email": email}), 200)

	assert sent_mail() == []


def test_email_change_requires_the_password():
	u = factories.user()

	assert_html(_security(u, {"password": "wrong", "new_email": "new@example.com"}), 200)

	assert sent_mail() == []


def test_email_change_to_the_current_address_is_refused():
	u = factories.user(email="same@example.com")

	assert_html(_security(u, {"password": factories.PASSWORD, "new_email": "Same@example.com"}), 200)

	assert sent_mail() == []


# Two-factor authentication

def test_enabling_two_factor_stores_the_secret():
	u = factories.user()
	secret = pyotp.random_base32()
	totp_step_settle()

	with db_diff() as d:
		r = _security(u, {"password": factories.PASSWORD, "2fa_secret": secret, "2fa_token": pyotp.TOTP(secret).now()})

	assert_html(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {"mfa_secret": secret}}})


@pytest.mark.parametrize("offset, accepted", [(-60, False), (-30, True), (30, True), (60, False)])
def test_two_factor_codes_are_accepted_one_step_either_side(offset, accepted):
	u = factories.user()
	secret = pyotp.random_base32()
	totp_step_settle()

	_security(u, {"password": factories.PASSWORD, "2fa_secret": secret, "2fa_token": pyotp.TOTP(secret).at(time.time() + offset)})

	assert (db.row("users", id=u["id"])["mfa_secret"] == secret) == accepted


def test_enabling_two_factor_requires_the_password():
	u = factories.user()
	secret = pyotp.random_base32()

	with db_diff() as d:
		r = _security(u, {"password": "wrong", "2fa_secret": secret, "2fa_token": pyotp.TOTP(secret).now()})

	assert_html(r, 200)
	d.assert_exactly()


def test_enabling_two_factor_requires_a_valid_code():
	u = factories.user()
	secret = pyotp.random_base32()

	with db_diff() as d:
		r = _security(u, {"password": factories.PASSWORD, "2fa_secret": secret, "2fa_token": _wrong_token(secret)})

	assert_html(r, 200)
	d.assert_exactly()


@pytest.mark.parametrize("secret", [None, "", "not base32!"])
def test_enabling_two_factor_with_a_missing_or_malformed_secret_is_refused(secret):
	u = factories.user()
	data = {"password": factories.PASSWORD, "2fa_token": "123456"}
	if secret is not None:
		data["2fa_secret"] = secret

	with db_diff() as d:
		r = _security(u, data)

	assert_html(r, 200)
	d.assert_exactly()


def test_enabling_two_factor_again_does_not_replace_the_secret():
	u = factories.user(mfa_secret=pyotp.random_base32())
	new_secret = pyotp.random_base32()

	with db_diff() as d:
		r = _security(u, {"password": factories.PASSWORD, "2fa_secret": new_secret, "2fa_token": pyotp.TOTP(new_secret).now()})

	assert_html(r, 200)
	d.assert_exactly()


@pytest.mark.parametrize("pad", ["", " "], ids=["exact", "padded"])
def test_two_factor_codes_may_carry_surrounding_spaces(pad):
	u = factories.user()
	secret = pyotp.random_base32()
	totp_step_settle()

	_security(u, {"password": factories.PASSWORD, "2fa_secret": secret, "2fa_token": f"{pad}{pyotp.TOTP(secret).now()}{pad}"})

	assert db.row("users", id=u["id"])["mfa_secret"] == secret


def test_disabling_two_factor_clears_the_secret():
	secret = pyotp.random_base32()
	u = factories.user(mfa_secret=secret)
	totp_step_settle()

	with db_diff() as d:
		r = _security(u, {"password": factories.PASSWORD, "2fa_remove": pyotp.TOTP(secret).now()})

	assert_html(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {"mfa_secret": None}}})


def test_disabling_two_factor_requires_the_password():
	secret = pyotp.random_base32()
	u = factories.user(mfa_secret=secret)

	with db_diff() as d:
		r = _security(u, {"password": "wrong", "2fa_remove": pyotp.TOTP(secret).now()})

	assert_html(r, 200)
	d.assert_exactly()


def test_disabling_two_factor_requires_a_valid_code():
	secret = pyotp.random_base32()
	u = factories.user(mfa_secret=secret)

	with db_diff() as d:
		r = _security(u, {"password": factories.PASSWORD, "2fa_remove": _wrong_token(secret)})

	assert_html(r, 200)
	d.assert_exactly()


def test_disabling_two_factor_when_not_enabled_is_refused():
	u = factories.user()

	with db_diff() as d:
		r = _security(u, {"password": factories.PASSWORD, "2fa_remove": "123456"})

	assert_html(r, 200)
	d.assert_exactly()


# Logging out other devices

def test_log_out_all_others_invalidates_other_sessions_but_keeps_this_one():
	u = factories.user()
	this, other = as_user(u), as_user(u)

	with db_diff() as d:
		r = this.post("/settings/log_out_all_others", {"password": factories.PASSWORD})

	assert_html(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {"login_nonce": u["login_nonce"] + 1}}})
	assert_redirect(this.get("/me"), f"/@{u['username']}")
	assert_api_unauthorized(other.get("/me", headers=XHR))


def test_log_out_all_others_ends_the_accounts_api_tokens():
	u = factories.user()
	token = factories.api_token(u)
	application_id = db.row("client_auths", access_token=token)["oauth_client"]
	factories.authorization(factories.user(), db.row("oauth_apps", id=application_id))
	elsewhere = factories.oauth_app(factories.user())
	factories.authorization(u, elsewhere)

	with db_diff() as d:
		as_user(u).post("/settings/log_out_all_others", {"password": factories.PASSWORD})

	d.assert_exactly(updated={"users": {u["id"]: {"login_nonce": u["login_nonce"] + 1}}}, deleted={"client_auths": [(u["id"], application_id), (u["id"], elsewhere["id"])]})
	assert_api_unauthorized(as_api(token).get("/me"))


def test_log_out_all_others_takes_the_password_verbatim():
	password = " spaced out password "
	u = factories.user(passhash=factories.passhash_for(password, factories.FAST_HASH_ITERATIONS))

	assert_html(as_user(u).post("/settings/log_out_all_others", {"password": password.strip()}), 401)
	assert_html(as_user(u).post("/settings/log_out_all_others", {"password": password}), 200)


def test_log_out_all_others_requires_the_password():
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).post("/settings/log_out_all_others", {"password": "wrong"})

	assert_html(r, 401)
	d.assert_exactly()
