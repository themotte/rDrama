from files.tests.spec.harness import *

XHR = {"xhr": "1"}


def test_session_cookie_identifies_the_user():
	u = factories.user()

	r = as_user(u).get("/me")

	assert_redirect(r, f"/@{u['username']}")


def test_anonymous_browser_is_sent_to_login_and_back():
	r = anon().get("/me", params={"a": "1"})

	assert_login_redirect(r, returning_to="/me?a=1")


def test_anonymous_xhr_gets_json_401():
	assert_api_unauthorized(anon().get("/me", headers=XHR))


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
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).post("/settings/profile", {"reddit": "reddit.com"}, headers=XHR)

	assert_status(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {"reddit": "reddit.com"}}})


def test_post_with_formkey_in_query_string_is_authenticated():
	u = factories.user()
	client = as_user(u)

	with db_diff() as d:
		r = client.post_raw(f"/settings/profile?formkey={client.formkey}", {"reddit": "reddit.com"}, headers=XHR)

	assert_status(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {"reddit": "reddit.com"}}})


def test_post_with_formkey_in_json_body_is_authenticated():
	client = as_user(factories.admin(level=3))

	r = client.post_json("/admin/update_filter_status", {"new_status": "normal"}, headers=XHR)

	assert_status(r, 404)


def test_post_without_formkey_is_treated_as_anonymous():
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.post_raw("/settings/profile", {"reddit": "reddit.com"}, headers=XHR)

	assert_api_unauthorized(r)
	d.assert_exactly()


def test_post_with_wrong_formkey_is_treated_as_anonymous():
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.post_raw("/settings/profile", {"reddit": "reddit.com", "formkey": "0" * 32}, headers=XHR)

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
