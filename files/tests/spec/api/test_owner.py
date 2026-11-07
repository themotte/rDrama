'''
What a user does with the API applications they requested.

GET /settings/apps lists the viewer's approved apps with their client ids and the token the viewer holds for each (approval gives the owner one; without one, the page links to authorizing the app, GET /authorize?client_id=<its client id>, which grants a new one), their pending requests, and the apps they have authorized (test_authorize), and offers the form that requests another (test_requests). Revoked apps and other users' apps aren't listed, and no one else's token ever shows: not those of users who authorized the viewer's apps, nor the viewer's tokens for other users' apps.

The owner of an app, and only they (others: 403), may:
- edit it (POST /edit_app/<id>: "name", "redirect_uri" and "description", by the rules of requesting: test_requests), which needs no new approval: an approved app keeps its client id and its tokens;
- delete it (POST /delete_app/<id>, which sends the owner back to /settings/apps), which ends every authorization of it. An app whose tokens made posts or comments is kept, revoked, so admins can still see where they came from (test_admin); to its owner it is gone like a deleted one;
- give an approved app a new client id (POST /oauth/reroll/<id>, answering a JSON "message" and the new client id as "id"), after which users authorize it under the new id only; tokens already granted keep working. A pending request has no client id to replace (409): only an admin's approval gives it one.

An id that is no app's (unknown, not a whole number, or too large), or a revoked app's, is 404.

Editing is refused to permanently suspended users (403).
'''
import pytest

from files.tests.spec.harness import *

OWNER_ROUTES = ["/edit_app/{}", "/delete_app/{}", "/oauth/reroll/{}"]
BAD_IDS = {
	"unknown": lambda: db.execute("SELECT nextval('oauth_apps_id_seq')"),
	"garbled": lambda: "abc",
	"huge": lambda: str(2**31),
	"revoked": lambda: factories.oauth_app(factories.user(), state="revoked")["id"],
}


def _edit_fields(**overrides):
	return {"name": factories.unique("app"), "redirect_uri": "https://example.com/other", "description": factories.unique(), **overrides}


# The settings page

def test_the_page_lists_the_viewers_apps_and_requests():
	owner = factories.user()
	approved, pending = factories.oauth_app(owner), factories.oauth_app(owner, state="pending")
	others = factories.oauth_app(factories.user())

	r = as_user(owner).get("/settings/apps")

	assert_html(r, 200)
	for token in (approved["app_name"], approved["client_id"], pending["app_name"]):
		assert_in_payload(r, token)
	assert_not_in_payload(r, others["app_name"])


def test_the_page_shows_the_owner_their_token():
	owner = factories.user()
	application = factories.oauth_app(owner)
	own = db.row("client_auths", oauth_client=application["id"], user_id=owner["id"])["access_token"]
	others = factories.authorization(factories.user(), application)

	r = as_user(owner).get("/settings/apps")

	assert_in_payload(r, own)
	assert_not_in_payload(r, others)


def test_an_owner_who_rescinded_their_token_is_shown_none():
	owner = factories.user()
	application = factories.oauth_app(owner)
	token = db.row("client_auths", oauth_client=application["id"])["access_token"]
	client = as_user(owner)
	client.post(f"/oauth/rescind/{application['id']}")

	r = client.get("/settings/apps")

	assert_not_in_payload(r, token)
	assert_in_payload(r, f"/authorize?client_id={application['client_id']}")


def test_the_page_lists_the_apps_the_viewer_authorized():
	viewer = factories.user()
	application = factories.oauth_app(factories.user())
	token = factories.authorization(viewer, application)

	r = as_user(viewer).get("/settings/apps")

	assert_in_payload(r, application["app_name"])
	assert_not_in_payload(r, application["client_id"])
	assert_not_in_payload(r, token)


def test_visitors_are_sent_to_log_in():
	assert_login_redirect(anon().get("/settings/apps"), "/settings/apps")


# Editing

def test_the_owner_edits_an_app():
	owner = factories.user()
	application = factories.oauth_app(owner, state="pending")
	fields = _edit_fields()

	with db_diff() as d:
		r = as_user(owner).post(f"/edit_app/{application['id']}", fields)

	assert_redirect(r, "/settings/apps")
	d.assert_exactly(updated={"oauth_apps": {application["id"]: {"app_name": fields["name"], "redirect_uri": fields["redirect_uri"], "description": fields["description"]}}})


def test_editing_an_approved_app_keeps_it_approved():
	owner = factories.user()
	application = factories.oauth_app(owner)
	token = db.row("client_auths", oauth_client=application["id"])["access_token"]
	fields = _edit_fields()

	with db_diff() as d:
		as_user(owner).post(f"/edit_app/{application['id']}", fields)

	d.assert_exactly(updated={"oauth_apps": {application["id"]: {"app_name": fields["name"], "redirect_uri": fields["redirect_uri"], "description": fields["description"]}}})
	assert as_api(token).get("/me").json["id"] == owner["id"]


def test_an_edited_description_is_cut_to_256_characters():
	owner = factories.user()
	application = factories.oauth_app(owner)
	kept = factories.unique("kept")

	as_user(owner).post(f"/edit_app/{application['id']}", _edit_fields(description=kept + "a" * (256 - len(kept)) + "cut"))

	assert db.row("oauth_apps", id=application["id"])["description"] == kept + "a" * (256 - len(kept))


def test_others_cant_edit_an_app():
	application = factories.oauth_app(factories.user())
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.post(f"/edit_app/{application['id']}", _edit_fields())

	assert_status(r, 403)
	d.assert_exactly()


def test_permanently_suspended_owners_cant_edit():
	owner = factories.user(is_banned=factories.admin(2)["id"], unban_utc=0)
	application = factories.oauth_app(owner)

	with db_diff() as d:
		r = as_user(owner).post(f"/edit_app/{application['id']}", _edit_fields())

	assert_status(r, 403)
	d.assert_exactly()


# Deleting

def test_the_owner_deletes_an_app_and_its_authorizations():
	owner, user = factories.user(), factories.user()
	application = factories.oauth_app(owner)
	factories.authorization(user, application)
	factories.authorization(user, factories.oauth_app(owner))

	with db_diff() as d:
		r = as_user(owner).post(f"/delete_app/{application['id']}")

	assert_redirect(r, "/settings/apps")
	d.assert_exactly(deleted={"oauth_apps": [application["id"]], "client_auths": [(owner["id"], application["id"]), (user["id"], application["id"])]})


def test_deleting_an_app_that_posted_keeps_it_revoked():
	owner = factories.user()
	application = factories.oauth_app(owner)
	factories.post(owner, app_id=application["id"])

	with db_diff() as d:
		as_user(owner).post(f"/delete_app/{application['id']}")

	d.assert_exactly(
		updated={"oauth_apps": {application["id"]: {"client_id": None, "revoked_utc": ANY}}},
		deleted={"client_auths": [(owner["id"], application["id"])]},
	)
	assert db.row("oauth_apps", id=application["id"])["revoked_utc"]


def test_the_page_leaves_out_revoked_apps():
	owner = factories.user()
	application = factories.oauth_app(owner, state="revoked")

	r = as_user(owner).get("/settings/apps")

	assert_html(r, 200)
	assert_not_in_payload(r, application["app_name"])


def test_others_cant_delete_an_app():
	application = factories.oauth_app(factories.user())
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.post(f"/delete_app/{application['id']}")

	assert_status(r, 403)
	d.assert_exactly()


# A new client id

def test_the_owner_gives_an_app_a_new_client_id():
	owner = factories.user()
	application = factories.oauth_app(owner)

	with db_diff() as d:
		r = as_user(owner).post(f"/oauth/reroll/{application['id']}")

	assert_status(r, 200)
	new_id = db.row("oauth_apps", id=application["id"])["client_id"]
	assert r.json == {"message": ANY, "id": new_id} and new_id != application["client_id"]
	d.assert_exactly(updated={"oauth_apps": {application["id"]: {"client_id": new_id}}})


def test_the_old_client_id_stops_working():
	owner = factories.user()
	application = factories.oauth_app(owner)
	as_user(owner).post(f"/oauth/reroll/{application['id']}")

	r = as_user(factories.user()).get("/authorize", params={"client_id": application["client_id"]})

	assert_status(r, 401)


def test_tokens_outlive_a_new_client_id():
	owner = factories.user()
	application = factories.oauth_app(owner)
	token = db.row("client_auths", oauth_client=application["id"])["access_token"]

	as_user(owner).post(f"/oauth/reroll/{application['id']}")

	assert as_api(token).get("/me").json["id"] == owner["id"]


def test_a_pending_request_cant_be_given_a_client_id():
	owner = factories.user()
	application = factories.oauth_app(owner, state="pending")

	with db_diff() as d:
		r = as_user(owner).post(f"/oauth/reroll/{application['id']}")

	assert_status(r, 409)
	d.assert_exactly()


def test_others_cant_give_an_app_a_new_client_id():
	application = factories.oauth_app(factories.user())
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.post(f"/oauth/reroll/{application['id']}")

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("bad", BAD_IDS)
@pytest.mark.parametrize("route", OWNER_ROUTES)
def test_ids_that_are_no_apps_are_not_found(route, bad):
	client = as_user(factories.user())
	path = route.format(BAD_IDS[bad]())

	with db_diff() as d:
		r = client.post(path, _edit_fields())

	assert_status(r, 404)
	d.assert_exactly()


@pytest.mark.parametrize("route", OWNER_ROUTES)
def test_api_clients_are_refused_before_the_id_is_looked_at(route):
	client = as_api(factories.api_token(factories.user()))

	with db_diff() as d:
		r = client.post(route.format("abc"), _edit_fields())

	assert_status(r, 403)
	d.assert_exactly()
