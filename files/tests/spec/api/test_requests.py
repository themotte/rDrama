'''
POST /api_keys requests an API application: "name", "redirect_uri" (where POST /authorize sends users with their token) and "description" (cut to 256 characters). The request is stored as a pending app owned by the requester, with no client id, and announced in modmail (notifications/test_modmail); then the requester is sent back to /settings/apps. Admins approve or refuse it (test_admin).

Permanently suspended users can't request apps (403).
'''
from files.tests.spec.harness import *


def _fields(**overrides):
	return {"name": factories.unique("app"), "redirect_uri": "https://example.com/callback", "description": factories.unique(), **overrides}


def test_a_request_stores_a_pending_app():
	user = factories.user()
	fields = _fields()

	with db_diff() as d:
		r = as_user(user).post("/api_keys", fields)

	assert_redirect(r, "/settings/apps")
	d.assert_exactly(inserted={
		"oauth_apps": [{"author_id": user["id"], "client_id": None, "app_name": fields["name"], "redirect_uri": fields["redirect_uri"], "description": fields["description"]}],
		"comments": [{}],
	})


def test_the_description_is_cut_to_256_characters():
	kept = factories.unique("kept")

	as_user(factories.user()).post("/api_keys", _fields(description=kept + "a" * (256 - len(kept)) + "cut"))

	assert db.rows("oauth_apps")[-1]["description"] == kept + "a" * (256 - len(kept))


def test_visitors_are_sent_to_log_in():
	with db_diff() as d:
		r = anon().post("/api_keys", _fields())

	assert_login_redirect(r, "/api_keys")
	d.assert_exactly()


def test_permanently_suspended_users_are_refused():
	client = as_user(factories.user(is_banned=factories.admin(2)["id"], unban_utc=0))

	with db_diff() as d:
		r = client.post("/api_keys", _fields())

	assert_status(r, 403)
	d.assert_exactly()
