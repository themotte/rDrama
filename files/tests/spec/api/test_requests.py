'''
POST /api_keys requests an API application: "name" (at most 50 characters), "redirect_uri" (where POST /authorize sends users with their token; at most 4096 characters) and "description" (cut to 256 characters, and may be empty). All three are required, the name and redirect URI are stripped of surrounding whitespace and must not be empty; otherwise the request is refused with 400, changing nothing. Editing an app (test_owner) takes the same fields by the same rules. Names are stored as typed and always shown as text. The request is stored as a pending app owned by the requester, with no client id, and announced in modmail (notifications/test_modmail); then the requester is sent back to /settings/apps. Admins approve or refuse it (test_admin).

Permanently suspended users can't request apps (403).
'''
import pytest

from files.tests.spec.harness import *

BAD_FIELDS = {
	"no name": {"name": None},
	"no redirect uri": {"redirect_uri": None},
	"no description": {"description": None},
	"blank name": {"name": "   "},
	"blank redirect uri": {"redirect_uri": " "},
	"long name": {"name": "a" * 51},
	"long redirect uri": {"redirect_uri": "https://example.com/" + "a" * 4077},
}


def _fields(**overrides):
	fields = {"name": factories.unique("app"), "redirect_uri": "https://example.com/callback", "description": factories.unique(), **overrides}
	return {k: v for k, v in fields.items() if v is not None}


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


def test_names_are_stored_as_typed():
	name = f"<b>{factories.unique('app')}</b>"

	as_user(factories.user()).post("/api_keys", _fields(name=name))

	assert db.rows("oauth_apps")[-1]["app_name"] == name


def test_names_are_shown_as_text():
	inner = factories.unique("app")
	application = factories.oauth_app(factories.user(), app_name=f"<b>{inner}</b>")

	r = as_user(factories.user()).get("/authorize", params={"client_id": application["client_id"]})

	assert_html(r, 200)
	assert_in_payload(r, inner)
	assert_not_in_payload(r, application["app_name"])


@pytest.mark.parametrize("length", [1, 50])
def test_names_of_1_to_50_characters_are_stored(length):
	name = factories.unique("app")[:length].ljust(length, "a")

	as_user(factories.user()).post("/api_keys", _fields(name=name))

	assert db.rows("oauth_apps")[-1]["app_name"] == name


def test_long_redirect_uris_are_stored():
	uri = "https://example.com/" + "a" * (4096 - len("https://example.com/"))

	assert_redirect(as_user(factories.user()).post("/api_keys", _fields(redirect_uri=uri)), "/settings/apps")

	assert db.rows("oauth_apps")[-1]["redirect_uri"] == uri


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


@pytest.mark.parametrize("bad", BAD_FIELDS)
@pytest.mark.parametrize("route", ["request", "edit"])
def test_bad_fields_are_refused(route, bad):
	owner = factories.user()
	path = "/api_keys" if route == "request" else f"/edit_app/{factories.oauth_app(owner)['id']}"
	client = as_user(owner)

	with db_diff() as d:
		r = client.post(path, _fields(**BAD_FIELDS[bad]))

	assert_status(r, 400)
	d.assert_exactly()


def test_names_and_redirect_uris_are_stripped_and_descriptions_may_be_empty():
	name = factories.unique("app")

	as_user(factories.user()).post("/api_keys", _fields(name=f"  {name} ", redirect_uri=" https://example.com/cb\n", description=""))

	application = db.rows("oauth_apps")[-1]
	assert (application["app_name"], application["redirect_uri"], application["description"]) == (name, "https://example.com/cb", "")
