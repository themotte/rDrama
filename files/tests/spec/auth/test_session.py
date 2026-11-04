'''
Who a request comes from (a session cookie, an API token, or nobody), the form key that proves a form came from the site, the `logged_in` marker cookie, and what every request must carry to be served at all.
'''
import time

import pytest

from files.tests.spec.harness import *

MARKER = "logged_in"


def test_session_cookie_identifies_the_user():
	u = factories.user()

	r = as_user(u).get("/me")

	assert_redirect(r, f"/@{u['username']}")


def test_anonymous_browser_is_sent_to_login_and_back():
	r = anon().get("/me", params={"a": "1"})

	assert_login_redirect(r, returning_to="/me?a=1")


def test_anonymous_xhr_gets_json_401():
	assert_api_unauthorized(anon().get("/me", headers=XHR))


def test_login_redirect_after_anonymous_post_does_not_carry_the_form_body():
	r = anon().post_raw("/settings/security", {"new_password": factories.unique("secret")})

	assert_login_redirect(r, returning_to="/settings/security")


def test_session_with_stale_login_nonce_is_anonymous_and_dropped():
	u = factories.user(login_nonce=1)
	client = as_user({**u, "login_nonce": 0})

	assert_api_unauthorized(client.get("/me", headers=XHR))
	assert "lo_user" not in client.session()


def test_session_for_deleted_account_is_anonymous_and_dropped():
	u = factories.user()
	client = as_user(u)
	db.delete("users", id=u["id"])

	assert_api_unauthorized(client.get("/me", headers=XHR))
	assert "lo_user" not in client.session()


def test_formkey_is_embedded_in_pages_for_logged_in_users():
	client = as_user(factories.user())

	assert client.get("/settings/profile").form_field("formkey") == client.formkey


def test_post_with_formkey_in_form_body_is_authenticated():
	u = factories.user(cardview=False)

	with db_diff() as d:
		r = as_user(u).post("/settings/profile", {"cardview": "true"}, headers=XHR)

	assert_status(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {"cardview": True}}})


def test_post_with_formkey_in_query_string_is_authenticated():
	u = factories.user(cardview=False)
	client = as_user(u)

	with db_diff() as d:
		r = client.post_raw(f"/settings/profile?formkey={client.formkey}", {"cardview": "true"}, headers=XHR)

	assert_status(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {"cardview": True}}})


def test_post_with_formkey_in_json_body_is_authenticated():
	client = as_user(factories.admin(level=3))

	r = client.post_json("/admin/update_filter_status", {"new_status": "normal"}, headers=XHR)

	assert_status(r, 404)


def test_a_json_body_that_is_not_an_object_carries_no_form_key():
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.request("POST", "/settings/profile", json=[client.formkey], headers=XHR)

	assert_api_unauthorized(r)
	d.assert_exactly()


def test_post_without_formkey_is_treated_as_anonymous():
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.post_raw("/settings/profile", {"cardview": "true"}, headers=XHR)

	assert_api_unauthorized(r)
	d.assert_exactly()


def test_post_with_wrong_formkey_is_treated_as_anonymous():
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.post_raw("/settings/profile", {"cardview": "true", "formkey": "0" * 32}, headers=XHR)

	assert_api_unauthorized(r)
	d.assert_exactly()


def test_login_with_password_sets_a_session():
	u = factories.user()
	client = anon()

	with db_diff() as d:
		r = client.post_raw("/login", {"username": u["username"], "password": factories.PASSWORD})

	assert_redirect(r, "/")
	assert client.user_id == u["id"]
	assert_redirect(client.get("/me"), f"/@{u['username']}")
	d.assert_exactly()


def test_login_session_cookie_attributes():
	u = factories.user()

	r = anon().post_raw("/login", {"username": u["username"], "password": factories.PASSWORD})

	cookie = next(c for c in r.header_all("Set-Cookie") if c.startswith("session_"))
	attributes = {part.strip().split("=")[0].lower() for part in cookie.split(";")[1:]}
	assert {"path", "expires", "httponly", "samesite"} <= attributes
	assert "Path=/" in cookie


def test_login_with_wrong_password_sets_no_session():
	u = factories.user()
	client = anon()

	with db_diff() as d:
		r = client.post_raw("/login", {"username": u["username"], "password": "wrong " + factories.PASSWORD})

	assert_status(r, 200)
	assert client.user_id is None
	d.assert_exactly()


def test_logout_ends_the_session():
	client = as_user(factories.user())

	r = client.get("/logout")

	assert_redirect(r, "/")
	assert client.user_id is None
	assert_api_unauthorized(client.get("/me", headers=XHR))


# The logged_in marker cookie: present exactly while the browser holds a logged-in session, so caches in front of the site can tell members apart without reading the session.

def _set_cookies(r, name):
	return [c for c in r.header_all("Set-Cookie") if c.startswith(f"{name}=")]


def test_logging_in_sets_the_marker_once():
	u = factories.user()
	client = anon()

	r = client.post_raw("/login", {"username": u["username"], "password": factories.PASSWORD})

	[cookie] = _set_cookies(r, MARKER)
	assert cookie.startswith(f"{MARKER}=1;") and "HttpOnly" in cookie and "SameSite=Lax" in cookie
	assert _set_cookies(client.get("/"), MARKER) == []


def test_logging_out_deletes_the_marker():
	client = as_user(factories.user())
	client.get("/")
	assert MARKER in client.cookies

	r = client.get("/logout")

	assert_redirect(r, "/")
	assert MARKER not in client.cookies


def test_a_session_ended_elsewhere_deletes_the_marker():
	u = factories.user()
	client = as_user(u)
	client.get("/")
	db.update("users", {"id": u["id"]}, login_nonce=u["login_nonce"] + 1)

	assert_html(client.get("/"), 200)

	assert MARKER not in client.cookies


def test_anonymous_visitors_never_get_the_marker():
	r = anon().get("/")

	assert_html(r, 200)
	assert _set_cookies(r, MARKER) == []


def test_static_files_do_not_resend_the_marker():
	client = as_user(factories.user())
	client.get("/")

	r = client.get("/assets/robots.txt")

	assert_status(r, 200)
	assert _set_cookies(r, MARKER) == []


def test_static_files_do_not_vary_on_cookies_for_a_fresh_visitor():
	r = anon().get("/assets/robots.txt")

	assert_status(r, 200)
	assert "cookie" not in (r.header("Vary") or "").lower()


# What every request must carry

def test_a_request_for_another_host_is_refused():
	r = anon().get("/", headers={"Host": "elsewhere.example"})

	assert_status(r, 403)
	assert "error" in r.json


def test_a_request_without_a_user_agent_is_refused():
	assert_status(anon().get("/", headers={"User-Agent": ""}), 403)


def test_api_clients_are_refused_while_bots_are_off():
	token = factories.api_token(factories.user())
	site_settings_set("Bots", False)

	assert_status(as_api(token).get("/me"), 403)


def test_an_api_token_identifies_its_account():
	u = factories.user()

	r = as_api(factories.api_token(u)).get("/me")

	assert_status(r, 200)
	assert (r.json["id"], r.json["username"]) == (u["id"], u["username"])


# Read-only mode

def test_read_only_mode_refuses_members_changes():
	u = factories.user(cardview=False)
	site_settings_set("Read-only mode", True)

	with db_diff() as d:
		r = as_user(u).post("/settings/profile", {"cardview": "true"}, headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


def test_read_only_mode_lets_admins_change_things():
	u = factories.admin(1, cardview=False)
	site_settings_set("Read-only mode", True)

	with db_diff() as d:
		r = as_user(u).post("/settings/profile", {"cardview": "true"}, headers=XHR)

	assert_status(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {"cardview": True}}})


# Ban evasion: an account created from a browser that held a banned account is shadowbanned on its first visit

def test_a_ban_evading_account_is_shadowbanned_on_its_next_request():
	u = factories.user(ban_evade=1)

	with db_diff() as d:
		assert_html(as_user(u).get("/"), 200)

	d.assert_exactly(updated={"users": {u["id"]: {"shadowbanned": "AutoJanny"}}})


@pytest.mark.parametrize("overrides", [{"admin_level": 2}, {"unban_utc": int(time.time()) + 86400}], ids=["admin", "with an unban date ahead"])
def test_some_ban_evading_accounts_are_left_alone(overrides):
	u = factories.user(ban_evade=1, **overrides)

	with db_diff() as d:
		assert_html(as_user(u).get("/"), 200)

	d.assert_exactly()


def test_a_permanently_suspended_account_cannot_change_its_name():
	admin = factories.admin(3)
	u = factories.user(is_banned=admin["id"], unban_utc=0)

	with db_diff() as d:
		r = as_user(u).post("/settings/name_change", {"name": factories.unique("name")}, headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


# Signing out everywhere (the account's login_nonce moving on) ends every session, however it began

def test_a_session_from_signing_up_ends_when_the_account_signs_out_everywhere():
	earlier = factories.user(login_nonce=5)
	factories.user()
	client = anon()
	client.post_raw("/login", {"username": earlier["username"], "password": factories.PASSWORD})
	client.get("/logout")
	form = client.get("/signup")
	username = factories.unique("new")
	client.post_raw("/signup", {"formkey": form.form_field("formkey"), "now": form.form_field("now"), "usernametwo": username, "email": "", "password": factories.PASSWORD, "password_confirm": factories.PASSWORD})
	new = db.row("users", username=username)
	db.update("users", {"id": new["id"]}, login_nonce=new["login_nonce"] + 1)

	assert_api_unauthorized(client.get("/me", headers=XHR))


def test_a_session_ahead_of_its_accounts_nonce_is_anonymous():
	u = factories.user(login_nonce=1)
	client = as_user({**u, "login_nonce": 2})

	assert_api_unauthorized(client.get("/me", headers=XHR))
