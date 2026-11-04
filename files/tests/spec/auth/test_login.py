'''
Logging in: GET /login shows the form; POST /login takes "username" (a username, either the current or the original one, with or without a leading "@", or an email) and "password", or, for an account with 2FA, a second POST with the challenge's "time" and "hash" and the "2fa_token" code. "redirect" names where to go afterwards. Logging in also records the browser's other accounts as alts.
'''
import time

import pyotp
import pytest

from files.tests.spec.harness import *


def _login(client, username, password=factories.PASSWORD, **extra):
	return client.post_raw("/login", {"username": username, "password": password, **extra})


# The form

def test_the_login_form():
	assert_html(anon().get("/login"), 200)


@pytest.mark.parametrize("target, landing", [("/settings/profile", "/settings/profile"), (f"{config.site_url()}/settings", "/settings"), ("/logged_out/settings/profile", "/settings/profile")])
def test_a_logged_in_visitor_is_sent_on_to_the_redirect(target, landing):
	r = as_user(factories.user()).get("/login", params={"redirect": target})

	assert_redirect(r, landing)


@pytest.mark.parametrize("target", ["https://elsewhere.example/x", "settings/profile"])
def test_a_redirect_off_the_site_shows_the_form_instead(target):
	assert_html(as_user(factories.user()).get("/login", params={"redirect": target}), 200)


# Logging in with a password

@pytest.mark.parametrize("name", ["exact", "upper", "at", "original"])
def test_any_form_of_the_username_logs_in(name):
	u = factories.user(original_username=factories.unique("orig"))
	username = {"exact": u["username"], "upper": u["username"].upper(), "at": "@" + u["username"], "original": u["original_username"]}[name]
	client = anon()

	assert_redirect(_login(client, username), "/")
	assert client.user_id == u["id"]


def test_an_email_logs_in_regardless_of_case():
	u = factories.user(email=f"{factories.unique()}@Example.com")
	client = anon()

	assert_redirect(_login(client, u["email"].upper()), "/")
	assert client.user_id == u["id"]


def test_an_email_shared_by_several_accounts_logs_into_none():
	email = f"{factories.unique()}@example.com"
	factories.user(email=email)
	factories.user(email=email)
	client = anon()

	assert_status(_login(client, email), 200)
	assert client.user_id is None


@pytest.mark.parametrize("iterations", [1000, 150000, 260000])
def test_stored_hashes_of_any_strength_log_in(iterations):
	u = factories.user(passhash=factories.passhash_for(factories.PASSWORD, iterations))
	client = anon()

	assert_redirect(_login(client, u["username"]), "/")
	assert client.user_id == u["id"]


def test_an_unknown_account_logs_into_nothing():
	client = anon()

	with db_diff() as d:
		r = _login(client, factories.unique("nobody"))

	assert_html(r, 200)
	assert client.user_id is None
	d.assert_exactly()


def test_a_system_account_cannot_log_in():
	client = anon()

	assert_html(_login(client, "AutoJanny", factories.PASSWORD), 200)
	assert client.user_id is None


def test_a_login_without_a_username_is_refused():
	assert_status(anon().post_raw("/login", {"password": factories.PASSWORD}), 400)


@pytest.mark.parametrize("target, landing", [("/settings/profile", "/settings/profile"), (f"{config.site_url()}/settings", "/settings"), ("/logged_out/settings/profile", "/settings/profile"), ("https://elsewhere.example/x", "/")])
def test_logging_in_goes_on_to_the_redirect_when_it_is_on_the_site(target, landing):
	u = factories.user()

	assert_redirect(_login(anon(), u["username"], redirect=target), landing)


# 2FA

def _two_factor_user():
	return factories.user(mfa_secret=pyotp.random_base32())


def _challenge(u, issued):
	return {"username": u["username"], "time": issued, "hash": session.sign(f"2fa-challenge+{u['id']}+{issued}+{u['login_nonce']}")}


def test_a_password_for_a_2fa_account_leads_to_the_challenge_without_logging_in():
	u = _two_factor_user()
	client = anon()

	r = _login(client, u["username"], redirect="/settings")

	assert_html(r, 200)
	assert r.form_field("hash") is not None and r.form_field("redirect") == "/settings"
	assert client.user_id is None


def test_the_code_answering_the_challenge_logs_in_and_goes_on_to_the_redirect():
	u = _two_factor_user()
	client = anon()
	totp_step_settle()

	r = client.post_raw("/login", {**_challenge(u, int(time.time())), "2fa_token": pyotp.TOTP(u["mfa_secret"]).now(), "redirect": "/settings"})

	assert_redirect(r, "/settings")
	assert client.user_id == u["id"]


@pytest.mark.parametrize("steps_back, logs_in", [(1, True), (2, False)])
def test_the_previous_code_is_still_accepted_but_not_older_ones(steps_back, logs_in):
	u = _two_factor_user()
	client = anon()
	totp_step_settle()

	client.post_raw("/login", {**_challenge(u, int(time.time())), "2fa_token": pyotp.TOTP(u["mfa_secret"]).at(time.time() - 30 * steps_back)})

	assert (client.user_id == u["id"]) == logs_in


def test_a_wrong_code_shows_the_challenge_again_without_logging_in():
	u = _two_factor_user()
	client = anon()
	totp_step_settle()
	wrong = f"{(int(pyotp.TOTP(u['mfa_secret']).now()) + 1) % 1000000:06d}"

	r = client.post_raw("/login", {**_challenge(u, int(time.time())), "2fa_token": wrong})

	assert_html(r, 200)
	assert r.form_field("hash") is not None
	assert client.user_id is None


def test_an_expired_challenge_goes_back_to_login():
	u = _two_factor_user()
	client = anon()
	totp_step_settle()

	r = client.post_raw("/login", {**_challenge(u, int(time.time()) - 601), "2fa_token": pyotp.TOTP(u["mfa_secret"]).now()})

	assert_redirect(r, "/login")
	assert client.user_id is None


def test_a_challenge_issued_for_another_account_goes_back_to_login():
	u = _two_factor_user()
	other = _two_factor_user()
	client = anon()
	totp_step_settle()

	r = client.post_raw("/login", {**_challenge(other, int(time.time())), "username": u["username"], "2fa_token": pyotp.TOTP(u["mfa_secret"]).now()})

	assert_redirect(r, "/login")
	assert client.user_id is None


# Alts: accounts logged into from the same browser are recorded as alts of each other

def test_logging_into_a_second_account_records_the_pair_as_alts():
	first, second = factories.user(), factories.user()
	client = anon()
	_login(client, first["username"])

	with db_diff() as d:
		_login(client, second["username"])

	d.assert_exactly(inserted={"alts": [{"user1": first["id"], "user2": second["id"], "is_manual": False}]})
	assert sorted(client.session()["history"]) == sorted([first["id"], second["id"]])


def test_each_earlier_account_is_paired_with_a_new_one():
	first, second, third = factories.user(), factories.user(), factories.user()
	client = anon()
	_login(client, first["username"])
	_login(client, second["username"])

	with db_diff() as d:
		_login(client, third["username"])

	d.assert_exactly(inserted={"alts": [{"user1": first["id"], "user2": third["id"]}, {"user1": second["id"], "user2": third["id"]}]})


def test_the_new_accounts_other_alts_do_not_stop_the_pair_being_recorded():
	first, second, unrelated = factories.user(), factories.user(), factories.user()
	db.insert("alts", user1=unrelated["id"], user2=second["id"], is_manual=True)
	client = anon()
	_login(client, first["username"])

	with db_diff() as d:
		_login(client, second["username"])

	d.assert_exactly(inserted={"alts": [{"user1": first["id"], "user2": second["id"]}]})


def test_a_pair_is_recorded_once():
	first, second = factories.user(), factories.user()
	client = anon()
	_login(client, first["username"])
	_login(client, second["username"])

	with db_diff() as d:
		_login(client, first["username"])

	d.assert_exactly()


def test_deleted_accounts_drop_out_of_the_history():
	gone, second = factories.user(), factories.user()
	client = anon()
	_login(client, gone["username"])
	db.delete("users", id=gone["id"])

	with db_diff() as d:
		_login(client, second["username"])

	d.assert_exactly()
	assert client.session()["history"] == [second["id"]]


def test_a_challenge_from_before_the_account_signed_out_everywhere_goes_back_to_login():
	u = _two_factor_user()
	challenge = _challenge(u, int(time.time()))
	db.update("users", {"id": u["id"]}, login_nonce=u["login_nonce"] + 1)
	client = anon()
	totp_step_settle()

	r = client.post_raw("/login", {**challenge, "2fa_token": pyotp.TOTP(u["mfa_secret"]).now()})

	assert_redirect(r, "/login")
	assert client.user_id is None


def test_after_a_wrong_code_the_right_one_still_logs_in_and_goes_on_to_the_redirect():
	u = _two_factor_user()
	client = anon()
	totp_step_settle()
	wrong = f"{(int(pyotp.TOTP(u['mfa_secret']).now()) + 1) % 1000000:06d}"
	again = client.post_raw("/login", {**_challenge(u, int(time.time())), "2fa_token": wrong, "redirect": "/settings"})

	r = client.post_raw("/login", {"username": again.form_field("username"), "time": again.form_field("time"), "hash": again.form_field("hash"), "redirect": again.form_field("redirect"), "2fa_token": pyotp.TOTP(u["mfa_secret"]).now()})

	assert_redirect(r, "/settings")
	assert client.user_id == u["id"]


def test_a_wrong_code_does_not_extend_the_challenge():
	u = _two_factor_user()
	issued = int(time.time()) - 300
	totp_step_settle()
	wrong = f"{(int(pyotp.TOTP(u['mfa_secret']).now()) + 1) % 1000000:06d}"

	r = anon().post_raw("/login", {**_challenge(u, issued), "2fa_token": wrong})

	assert_html(r, 200)
	assert r.form_field("time") == str(issued)


@pytest.mark.parametrize("fields", [{}, {"password": ""}, {"time": "soon", "hash": "0" * 32, "2fa_token": "000000"}], ids=["nothing", "empty password", "non-integer time"])
def test_a_login_with_neither_password_nor_challenge_is_refused(fields):
	u = factories.user()

	assert_status(anon().post_raw("/login", {"username": u["username"], **fields}), 400)
