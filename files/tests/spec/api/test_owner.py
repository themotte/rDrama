'''
What a user does with the API applications they requested.

GET /settings/apps lists the viewer's approved apps with their client ids, their pending requests, and the apps they have authorized (test_authorize), and offers the form that requests another (test_requests). Other users' apps aren't listed.

The owner of an app, and only they (others: 403), may:
- edit it (POST /edit_app/<id>: "name", "redirect_uri", "description" cut to 256 characters, as when requesting), which needs no new approval: an approved app keeps its client id and its tokens;
- delete it (POST /delete_app/<id>), which ends every authorization of it;
- give an approved app a new client id (POST /oauth/reroll/<id>, answering a JSON "message" and the new client id as "id"), after which users authorize it under the new id only; tokens already granted keep working. A pending request has no client id to replace (409): only an admin's approval gives it one.

Editing is refused to permanently suspended users (403).
'''
from files.tests.spec.harness import *


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


def test_the_page_lists_the_apps_the_viewer_authorized():
	viewer = factories.user()
	application = factories.oauth_app(factories.user())
	factories.authorization(viewer, application)

	r = as_user(viewer).get("/settings/apps")

	assert_in_payload(r, application["app_name"])
	assert_not_in_payload(r, application["client_id"])


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

	assert_status(r, 302)
	d.assert_exactly(deleted={"oauth_apps": [application["id"]], "client_auths": [(owner["id"], application["id"]), (user["id"], application["id"])]})


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
