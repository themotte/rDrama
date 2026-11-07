'''
API clients authenticate each request with an access token (one per user per app: test_authorize) sent as the whole Authorization header, with no scheme such as "Bearer"; whitespace around it is ignored. A token of an approved app authenticates as the user who holds it, whatever session cookie the request also carries, and needs no form key. Any other token, including one for an app that isn't approved, authenticates no one: routes that need a login answer 401, and pages open to everyone are served as to a logged-out client. A header of only whitespace carries no token, and the session counts.

GET /me (or /@me) answers an API client with the authenticated user's JSON.

API clients get errors as a JSON object: "code" (the status), "error" and "description" (readable text), and "details" (why the request was refused, when the refusal says, else null).
'''
from files.tests.spec.harness import *


def test_a_token_authenticates_its_holder():
	user = factories.user()

	r = as_api(factories.api_token(user)).get("/me")

	assert_status(r, 200)
	assert r.json["id"] == user["id"]


def test_whitespace_around_the_token_is_ignored():
	user = factories.user()

	r = as_api(f"  {factories.api_token(user)}\t").get("/me")

	assert r.json["id"] == user["id"]


def test_a_scheme_before_the_token_makes_it_unknown():
	assert_api_unauthorized(as_api(f"Bearer {factories.api_token(factories.user())}").get("/me"))


def test_a_token_overrides_the_session():
	holder = factories.user()
	client = as_user(factories.user())
	client.authorization = factories.api_token(holder)

	assert client.get("/me").json["id"] == holder["id"]


def test_a_blank_header_leaves_the_session():
	user = factories.user()
	client = as_user(user)
	client.authorization = "   "

	assert client.get("/me").json["id"] == user["id"]


def test_tokens_for_pending_apps_authenticate_no_one():
	user = factories.user()
	token = factories.authorization(user, factories.oauth_app(user, state="pending"))

	assert_api_unauthorized(as_api(token).get("/me"))


def test_unknown_tokens_are_served_open_pages():
	author = factories.user()
	post = factories.post(author)

	r = as_api(factories.unique()).get(f"/@{author['username']}/posts")

	assert_status(r, 200)
	assert [p["id"] for p in r.json["data"]] == [post["id"]]


def test_api_clients_change_things_without_a_form_key():
	user = factories.user(cardview=False)
	client = as_api(factories.api_token(user))

	with db_diff() as d:
		r = client.post("/settings/profile", {"cardview": "true"})

	assert_status(r, 200)
	d.assert_exactly(updated={"users": {user["id"]: {"cardview": True}}})


def test_errors_are_json():
	r = as_api(factories.api_token(factories.user())).get(f"/@{factories.unique('nobody')}")

	assert_status(r, 404)
	assert r.json == {"code": 404, "error": ANY, "description": ANY, "details": None}


def test_refusals_say_why():
	r = as_api(factories.api_token(factories.admin(3))).get("/admin")

	assert_status(r, 403)
	assert set(r.json) == {"code", "error", "description", "details"}
	assert r.json["code"] == 403 and r.json["details"]
