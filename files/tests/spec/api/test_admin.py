'''
Admins review API applications (who may: admin/test_access).

- GET /admin/apps (level 2) lists every app, with its owner and client id; revoked apps are listed with no actions, and approval is offered only to admins who may approve.
- POST /admin/app/approve/<id> (level 3) approves a pending app: it gets a client id, its owner gets a token for it and is notified (the token itself shows only on the owner's /settings/apps, never in the notice), and the approval is logged in the mod log ("approve_app", against the owner).
- POST /admin/app/reject/<id> (level 2) refuses a pending request, and POST /admin/app/revoke/<id> (level 2) withdraws an approved app: either way every authorization of the app is deleted, and so is the app, unless its tokens made posts or comments: then it is kept, revoked, for the app pages below; the owner is notified, and the action is logged ("reject_app" or "revoke_app", against the owner).

Each answers a JSON message, and refuses an app in another state (revoked apps included) with 409, changing nothing. Approving keeps a token the owner already holds for the app. An id that is no app's (unknown, not a whole number, or too large) is 404, here and on the app pages below.

GET /admin/app/<id> and GET /admin/app/<id>/comments (level 2) show an app and the posts or comments its tokens made, newest first, 100 to a page, each shown as admin listings show them (listings/test_parameters), leaving out posts and comments by shadowbanned users.
'''
import pytest

from files.tests.spec.harness import *

ADMIN_ROUTES = [("POST", "/admin/app/approve/{}"), ("POST", "/admin/app/reject/{}"), ("POST", "/admin/app/revoke/{}"), ("GET", "/admin/app/{}"), ("GET", "/admin/app/{}/comments")]
BAD_IDS = {
	"unknown": lambda: db.execute("SELECT nextval('oauth_apps_id_seq')"),
	"garbled": lambda: "abc",
	"huge": lambda: str(2**31),
}


def test_the_list_shows_every_app():
	pending, approved = factories.oauth_app(factories.user(), state="pending"), factories.oauth_app(factories.user())

	r = as_user(factories.admin(2)).get("/admin/apps")

	assert_html(r, 200)
	for token in (pending["app_name"], approved["app_name"], approved["client_id"]):
		assert_in_payload(r, token)


def test_approving_gives_the_app_a_client_id_and_its_owner_a_token():
	owner, admin = factories.user(), factories.admin(3)
	application = factories.oauth_app(owner, state="pending")

	with db_diff() as d:
		r = as_user(admin).post(f"/admin/app/approve/{application['id']}")

	assert_json_message(r)
	client_id = db.row("oauth_apps", id=application["id"])["client_id"]
	assert client_id
	d.assert_exactly(
		updated={"oauth_apps": {application["id"]: {"client_id": client_id}}},
		inserted={
			"client_auths": [{"user_id": owner["id"], "oauth_client": application["id"]}],
			"comments": [{"author_id": seed.SYSTEM_ID, "parent_submission": None, "sentto": None}],
			"notifications": [{"user_id": owner["id"]}],
			"modactions": [{"kind": "approve_app", "user_id": admin["id"], "target_user_id": owner["id"]}],
		},
	)


def test_the_owners_token_works_once_approved():
	owner = factories.user()
	application = factories.oauth_app(owner, state="pending")

	as_user(factories.admin(3)).post(f"/admin/app/approve/{application['id']}")

	token = db.row("client_auths", oauth_client=application["id"])["access_token"]
	assert as_api(token).get("/me").json["id"] == owner["id"]


def test_the_approval_notice_doesnt_carry_the_token():
	owner = factories.user()
	application = factories.oauth_app(owner, state="pending")

	as_user(factories.admin(3)).post(f"/admin/app/approve/{application['id']}")

	token = db.row("client_auths", oauth_client=application["id"])["access_token"]
	[notification] = db.rows("notifications", user_id=owner["id"])
	assert token not in db.row("comments", id=notification["comment_id"])["body_html"]


def test_rejecting_deletes_the_request():
	owner, admin = factories.user(), factories.admin(2)
	application = factories.oauth_app(owner, state="pending")

	with db_diff() as d:
		r = as_user(admin).post(f"/admin/app/reject/{application['id']}")

	assert_json_message(r)
	d.assert_exactly(
		deleted={"oauth_apps": [application["id"]]},
		inserted={
			"comments": [{"author_id": seed.SYSTEM_ID, "parent_submission": None, "sentto": None}],
			"notifications": [{"user_id": owner["id"]}],
			"modactions": [{"kind": "reject_app", "user_id": admin["id"], "target_user_id": owner["id"]}],
		},
	)


def test_revoking_deletes_the_app_and_its_authorizations():
	owner, user, admin = factories.user(), factories.user(), factories.admin(2)
	application = factories.oauth_app(owner)
	token = factories.authorization(user, application)
	factories.authorization(user, factories.oauth_app(owner))

	with db_diff() as d:
		r = as_user(admin).post(f"/admin/app/revoke/{application['id']}")

	assert_json_message(r)
	d.assert_exactly(
		deleted={"oauth_apps": [application["id"]], "client_auths": [(owner["id"], application["id"]), (user["id"], application["id"])]},
		inserted={
			"comments": [{"author_id": seed.SYSTEM_ID, "parent_submission": None, "sentto": None}],
			"notifications": [{"user_id": owner["id"]}],
			"modactions": [{"kind": "revoke_app", "user_id": admin["id"], "target_user_id": owner["id"]}],
		},
	)
	assert_api_unauthorized(as_api(token).get("/me"))


def test_revoking_an_app_that_posted_keeps_it_revoked():
	owner = factories.user()
	application = factories.oauth_app(owner)
	factories.comment(owner, factories.post(factories.user()), app_id=application["id"])
	client = as_user(factories.admin(2))

	with db_diff() as d:
		client.post(f"/admin/app/revoke/{application['id']}")

	d.assert_exactly(
		updated={"oauth_apps": {application["id"]: {"client_id": None, "revoked_utc": ANY}}},
		deleted={"client_auths": [(owner["id"], application["id"])]},
		inserted={"comments": [{}], "notifications": [{}], "modactions": [{"kind": "revoke_app"}]},
	)


def test_the_list_offers_no_actions_on_revoked_apps():
	application = factories.oauth_app(factories.user(), state="revoked")

	r = as_user(factories.admin(3)).get("/admin/apps")

	assert_in_payload(r, application["app_name"])
	for action in ("approve", "reject", "revoke"):
		assert_not_in_payload(r, f"/admin/app/{action}/{application['id']}")


@pytest.mark.parametrize("page", ["/admin/apps", "/admin/app/{}"])
@pytest.mark.parametrize("level", [2, 3])
def test_approval_is_offered_from_level_3(page, level):
	application = factories.oauth_app(factories.user(), state="pending")

	r = as_user(factories.admin(level)).get(page.format(application["id"]))

	assert_in_payload(r, f"/admin/app/reject/{application['id']}")
	(assert_in_payload if level == 3 else assert_not_in_payload)(r, f"/admin/app/approve/{application['id']}")


def test_a_revoked_apps_page_still_shows_its_posts():
	application = factories.oauth_app(factories.user(), state="revoked")
	post = factories.post(factories.user(), app_id=application["id"])

	r = as_user(factories.admin(2)).get(f"/admin/app/{application['id']}")

	assert_html(r, 200)
	assert_in_payload(r, post["title"])


def test_the_app_page_shows_its_posts():
	application = factories.oauth_app(factories.user())
	post = factories.post(factories.user(), app_id=application["id"])
	other = factories.post(factories.user())

	r = as_user(factories.admin(2)).get(f"/admin/app/{application['id']}")

	assert_html(r, 200)
	assert_in_payload(r, application["app_name"])
	assert_in_payload(r, post["title"])
	assert_not_in_payload(r, other["title"])


def _app_page_lists_100_items(kind):
	application = factories.oauth_app(factories.user())
	author, post = factories.user(), factories.post(factories.user())
	made = lambda i: factories.post(author, app_id=application["id"], created_utc=1000 + i, title=factories.unique()) if kind == "posts" else factories.comment(author, post, app_id=application["id"], created_utc=1000 + i)
	items = [made(i) for i in range(101)]
	text = "title" if kind == "posts" else "body"

	r = as_user(factories.admin(2)).get(f"/admin/app/{application['id']}" + ("/comments" if kind == "comments" else ""))

	assert_in_payload(r, items[1][text])
	assert_not_in_payload(r, items[0][text])


def test_the_app_page_shows_100_posts_at_a_time():
	_app_page_lists_100_items("posts")


def test_the_app_comments_page_shows_100_comments_at_a_time():
	_app_page_lists_100_items("comments")


def test_the_app_comments_page_shows_its_comments():
	application = factories.oauth_app(factories.user())
	post = factories.post(factories.user())
	comment = factories.comment(factories.user(), post, app_id=application["id"])
	other = factories.comment(factories.user(), post)

	r = as_user(factories.admin(2)).get(f"/admin/app/{application['id']}/comments")

	assert_html(r, 200)
	assert_in_payload(r, comment["body"])
	assert_not_in_payload(r, other["body"])


@pytest.mark.parametrize("action, state", [("approve", "approved"), ("reject", "approved"), ("revoke", "pending"), ("approve", "revoked"), ("reject", "revoked"), ("revoke", "revoked")])
def test_actions_refuse_apps_in_another_state(action, state):
	application = factories.oauth_app(factories.user(), state=state)
	client = as_user(factories.admin(3))

	with db_diff() as d:
		r = client.post(f"/admin/app/{action}/{application['id']}")

	assert_status(r, 409)
	d.assert_exactly()


def test_approving_keeps_a_token_the_owner_holds():
	owner = factories.user()
	application = factories.oauth_app(owner, state="pending")
	token = factories.authorization(owner, application)

	r = as_user(factories.admin(3)).post(f"/admin/app/approve/{application['id']}")

	assert_json_message(r)
	assert db.row("client_auths", oauth_client=application["id"])["access_token"] == token


@pytest.mark.parametrize("bad", BAD_IDS)
@pytest.mark.parametrize("method, route", ADMIN_ROUTES, ids=[f"{m} {r}" for m, r in ADMIN_ROUTES])
def test_ids_that_are_no_apps_are_not_found(method, route, bad):
	client = as_user(factories.admin(3))
	path = route.format(BAD_IDS[bad]())

	with db_diff() as d:
		r = client.get(path) if method == "GET" else client.post(path)

	assert_status(r, 404)
	d.assert_exactly()


@pytest.mark.parametrize("kind", ["posts", "comments"])
def test_the_app_pages_leave_out_shadowbanned_users_items(kind):
	application = factories.oauth_app(factories.user())
	author, post = factories.user(shadowbanned="somemod"), factories.post(factories.user())
	item = factories.post(author, app_id=application["id"]) if kind == "posts" else factories.comment(author, post, app_id=application["id"])

	r = as_user(factories.admin(2)).get(f"/admin/app/{application['id']}" + ("/comments" if kind == "comments" else ""))

	assert_html(r, 200)
	assert_not_in_payload(r, item["title"] if kind == "posts" else item["body"])
