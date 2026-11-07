'''
How users let an API application act for them.

The app sends the user to GET /authorize?client_id=<its client id>, which asks the logged-in user to authorize it (visitors are sent to log in and come back). Submitting that (POST /authorize with "client_id") grants the user a token for the app, one per user per app: authorizing again gives the same token. The user's browser is then sent to the app's redirect URI with the token as the "token" query parameter, and the app acts for the user with it (test_tokens). Suspended users may authorize apps.

A client id no approved app has is answered, page and form alike, with 401 and the JSON object {"oauth_error": <text>}, changing nothing.
'''
import pytest

from files.tests.spec.harness import *


def test_the_page_asks_the_user_about_the_app():
	application = factories.oauth_app(factories.user())

	r = as_user(factories.user()).get("/authorize", params={"client_id": application["client_id"]})

	assert_html(r, 200)
	assert_in_payload(r, application["app_name"])
	assert r.form_field("client_id") == application["client_id"]


def test_visitors_are_sent_to_log_in_and_back():
	application = factories.oauth_app(factories.user())

	r = anon().get("/authorize", params={"client_id": application["client_id"]})

	assert_login_redirect(r, f"/authorize?client_id={application['client_id']}")


def test_authorizing_grants_a_token_and_sends_it_to_the_app():
	user, application = factories.user(), factories.oauth_app(factories.user())

	with db_diff() as d:
		r = as_user(user).post("/authorize", {"client_id": application["client_id"]})

	[granted] = d.inserted["client_auths"]
	d.assert_exactly(inserted={"client_auths": [{"user_id": user["id"], "oauth_client": application["id"]}]})
	assert_status(r, 302)
	assert r.location == f"{application['redirect_uri']}?token={granted['access_token']}"
	assert as_api(granted["access_token"]).get("/me").json["id"] == user["id"]


def test_authorizing_again_gives_the_same_token():
	user, application = factories.user(), factories.oauth_app(factories.user())
	token = factories.authorization(user, application)

	with db_diff() as d:
		r = as_user(user).post("/authorize", {"client_id": application["client_id"]})

	assert r.location == f"{application['redirect_uri']}?token={token}"
	d.assert_exactly()


def test_suspended_users_may_authorize():
	user = factories.user(is_banned=factories.admin(2)["id"], unban_utc=0)
	application = factories.oauth_app(factories.user())

	with db_diff() as d:
		as_user(user).post("/authorize", {"client_id": application["client_id"]})

	d.assert_exactly(inserted={"client_auths": [{"user_id": user["id"], "oauth_client": application["id"]}]})


@pytest.mark.parametrize("method", ["get", "post"])
def test_unknown_client_ids_are_refused(method):
	factories.oauth_app(factories.user())
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.get("/authorize", params={"client_id": factories.unique()}) if method == "get" else client.post("/authorize", {"client_id": factories.unique()})

	assert_status(r, 401)
	assert set(r.json) == {"oauth_error"}
	d.assert_exactly()
