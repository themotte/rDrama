'''
Resetting a forgotten password: POST /forgot with "username" and "email" mails a reset link (formats in harness/session.py) when they match an account, and says the same either way; the link (GET /reset?id=&time=&token=) opens a form, and POSTing it ("user_id", "time", "token", "password", "confirm_password") sets the password. Link and form expire ten minutes after the link was issued.
'''
import time

import pytest

from files.tests.spec.harness import *


def _member():
	return factories.user(email=f"{factories.unique()}@example.com")


def _link(u, issued, **overrides):
	return {"id": u["id"], "time": issued, "token": session.sign(f"forgot+{u['id']}+{issued}+{u['login_nonce']}"), **overrides}


def _form(u, issued, password, **overrides):
	return {"user_id": u["id"], "time": issued, "token": session.sign(f"reset+{u['id']}+{issued}+{u['login_nonce']}"), "password": password, "confirm_password": password, **overrides}


# Asking for a link

def test_the_request_form():
	assert_html(anon().get("/forgot"), 200)


@pytest.mark.parametrize("variant", ["exact", "case", "at"])
def test_a_matching_username_and_email_get_a_reset_link(variant):
	u = _member()
	username, email = {"exact": (u["username"], u["email"]), "case": (u["username"].upper(), u["email"].upper()), "at": ("@" + u["username"], u["email"])}[variant]

	r = anon().post("/forgot", {"username": username, "email": email})

	assert_html(r, 200)
	[mail] = sent_mail()
	assert mail["to"] == [u["email"]]


@pytest.mark.parametrize("mismatch", ["username", "email"])
def test_a_mismatch_gets_the_same_page_and_no_mail(mismatch):
	u = _member()
	fields = {"username": u["username"], "email": u["email"], mismatch: {"username": factories.unique("nobody"), "email": "other@example.com"}[mismatch]}

	assert_html(anon().post("/forgot", fields), 200)

	assert sent_mail() == []


def test_an_invalid_email_is_refused_without_mail():
	u = _member()

	assert_html(anon().post("/forgot", {"username": u["username"], "email": "not-an-email"}), 200)

	assert sent_mail() == []


def test_asking_without_a_username_is_refused():
	assert_status(anon().post("/forgot", {"email": "a@example.com"}), 400)


# Opening the link

def test_an_expired_link_opens_no_form():
	u = _member()

	r = anon().get("/reset", params=_link(u, int(time.time()) - 601))

	assert_html(r, 200)
	assert r.form_field("token") is None


def test_a_link_signed_for_another_account_is_refused():
	u, other = _member(), _member()

	assert_status(anon().get("/reset", params=_link(other, int(time.time()), id=u["id"])), 400)


def test_a_link_for_an_unknown_account_is_refused():
	u = _member()
	db.delete("users", id=u["id"])

	assert_status(anon().get("/reset", params=_link(u, int(time.time()))), 400)


# Setting the password

def test_the_old_password_stops_working():
	u = _member()

	anon().post_raw("/reset", _form(u, int(time.time()), f"new {factories.unique()} password"))

	assert not can_log_in(u, factories.PASSWORD)


def test_passwords_that_differ_show_the_form_again():
	u = _member()

	with db_diff() as d:
		r = anon().post_raw("/reset", _form(u, int(time.time()), "first password", confirm_password="second password"))

	assert_html(r, 200)
	assert r.form_field("token") is not None
	d.assert_exactly()


def test_an_expired_form_sets_nothing():
	u = _member()

	with db_diff() as d:
		r = anon().post_raw("/reset", _form(u, int(time.time()) - 601, f"new {factories.unique()} password"))

	assert_html(r, 200)
	d.assert_exactly()


def test_a_form_with_a_bad_token_is_refused():
	u = _member()

	with db_diff() as d:
		r = anon().post_raw("/reset", _form(u, int(time.time()), f"new {factories.unique()} password", token="0" * 32))

	assert_status(r, 400)
	d.assert_exactly()


def test_a_logged_in_browser_resets_like_anyone():
	'''The reset form carries no form key of the logged-in account, so the browser's session doesn't count.'''
	u = _member()
	new_password = f"new {factories.unique()} password"

	r = as_user(factories.user()).post_raw("/reset", _form(u, int(time.time()), new_password))

	assert_html(r, 200)
	assert can_log_in(u, new_password)


def test_an_api_client_is_sent_home():
	'''Only an API client reaches this: it is identified by its token rather than by a form key.'''
	u = _member()
	client = as_api(factories.api_token(factories.user()))

	with db_diff() as d:
		r = client.post_raw("/reset", _form(u, int(time.time()), f"new {factories.unique()} password"))

	assert_redirect(r, "/")
	d.assert_exactly()


# A reset signs the account out everywhere and spends its links

def test_a_reset_ends_the_accounts_sessions():
	u = _member()
	elsewhere = as_user(u)

	anon().post_raw("/reset", _form(u, int(time.time()), f"new {factories.unique()} password"))

	assert_api_unauthorized(elsewhere.get("/me", headers=XHR))


def test_a_reset_link_works_once():
	u = _member()
	issued = int(time.time())
	anon().post_raw("/reset", _form(u, issued, f"new {factories.unique()} password"))

	assert_status(anon().get("/reset", params=_link(u, issued)), 400)


# Malformed requests

@pytest.mark.parametrize("field, value", [("time", "soon"), ("id", "someone")])
def test_a_reset_link_with_a_malformed_field_is_refused(field, value):
	u = _member()

	assert_status(anon().get("/reset", params=_link(u, int(time.time()), **{field: value})), 400)


@pytest.mark.parametrize("missing", ["time", "password"])
def test_a_reset_form_missing_a_field_is_refused(missing):
	u = _member()
	fields = _form(u, int(time.time()), f"new {factories.unique()} password")
	del fields[missing]

	with db_diff() as d:
		r = anon().post_raw("/reset", fields)

	assert_status(r, 400)
	d.assert_exactly()


def test_a_reset_form_for_an_unknown_account_is_refused():
	u = _member()
	fields = _form(u, int(time.time()), f"new {factories.unique()} password")
	db.delete("users", id=u["id"])

	assert_status(anon().post_raw("/reset", fields), 400)


@pytest.mark.parametrize("password", ["", "short", "x" * 101])
def test_a_password_of_the_wrong_length_shows_the_form_again(password):
	u = _member()

	with db_diff() as d:
		r = anon().post_raw("/reset", _form(u, int(time.time()), password))

	assert_html(r, 200)
	assert r.form_field("token") is not None
	d.assert_exactly()
