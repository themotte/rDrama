'''
A user's public details as JSON, for logged-in users: GET /@<username>/info (case-insensitively, by current or original username) and GET /<user id>/info.

The object has "username", "url" (the profile path), "id", "is_banned", "post_count" and "comment_count". The counts read 0 for a shadowbanned user or a private profile, except to the user themselves and admins (level 2 and up), as nobody else sees their posts and comments. User search (GET /search/users) answers API clients with the same objects, counts included. While the user is suspended (banned permanently, or temporarily and the ban hasn't run out) it adds only "is_permanent_ban" and "ban_reason", with "is_banned" true; otherwise it adds "created_utc", "is_private", "profile_url", "bannerurl", "bio", "bio_html", "flair", and "is_banned" says whether the account carries a ban at all (an expired one included).

A user blocking the viewer, or blocked by them, refuses them with 403. An unknown user (or an id that isn't a number) is 404; anonymous browsers are sent to log in.
'''
import time

import pytest

from files.tests.spec.harness import *

ROUTES = {
	"by name": lambda user: f"/@{user['username']}/info",
	"by id": lambda user: f"/{user['id']}/info",
}

UNSUSPENDED_KEYS = {"username", "url", "id", "is_banned", "created_utc", "is_private", "profile_url", "bannerurl", "bio", "bio_html", "flair", "post_count", "comment_count"}
SUSPENDED_KEYS = {"username", "url", "id", "is_banned", "is_permanent_ban", "ban_reason", "post_count", "comment_count"}


@pytest.mark.parametrize("route", ROUTES)
def test_info_describes_the_user(route):
	bio, flair = factories.unique(), factories.unique()
	user = factories.user(bio=bio, bio_html=f"<p>{bio}</p>", customtitle=flair, created_utc=1_700_000_000)
	factories.post(user)
	factories.comment(user, factories.post(factories.user()))

	r = as_user(factories.user()).get(ROUTES[route](user))

	assert_status(r, 200)
	assert set(r.json) == UNSUSPENDED_KEYS
	assert {k: r.json[k] for k in UNSUSPENDED_KEYS - {"profile_url", "bannerurl"}} == {
		"username": user["username"],
		"url": f"/@{user['username']}",
		"id": user["id"],
		"is_banned": False,
		"created_utc": 1_700_000_000,
		"is_private": False,
		"bio": bio,
		"bio_html": f"<p>{bio}</p>",
		"flair": flair,
		"post_count": 1,
		"comment_count": 1,
	}
	assert isinstance(r.json["profile_url"], str) and isinstance(r.json["bannerurl"], str)


def _shadowbanned_with_content():
	user = factories.user()
	factories.post(user)
	factories.comment(user, factories.post(factories.user()))
	db.update("users", {"id": user["id"]}, shadowbanned="somemod")
	return user


@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("viewer", ["other user", "shadowbanned user"])
def test_info_of_a_shadowbanned_user_shows_no_activity_to_others(route, viewer):
	user = _shadowbanned_with_content()

	r = as_user(factories.user(shadowbanned="somemod" if viewer == "shadowbanned user" else None)).get(ROUTES[route](user))

	assert_status(r, 200)
	assert (r.json["post_count"], r.json["comment_count"]) == (0, 0)


@pytest.mark.parametrize("viewer", ["themselves", "admin"])
def test_info_of_a_shadowbanned_user_shows_activity_to_themselves_and_admins(viewer):
	user = _shadowbanned_with_content()
	client = as_user(user) if viewer == "themselves" else as_user(factories.admin(2))

	r = client.get(f"/@{user['username']}/info")

	assert_status(r, 200)
	assert (r.json["post_count"], r.json["comment_count"]) == (1, 1)


@pytest.mark.parametrize("route", ROUTES)
def test_info_of_a_private_user_shows_no_activity_to_others(route):
	user = factories.user(is_private=True)
	factories.post(user)
	factories.comment(user, factories.post(factories.user()))

	r = as_user(factories.user()).get(ROUTES[route](user))

	assert_status(r, 200)
	assert (r.json["post_count"], r.json["comment_count"]) == (0, 0)


@pytest.mark.parametrize("viewer", ["themselves", "admin"])
def test_info_of_a_private_user_shows_activity_to_themselves_and_admins(viewer):
	user = factories.user(is_private=True)
	factories.post(user)
	factories.comment(user, factories.post(factories.user()))
	client = as_user(user) if viewer == "themselves" else as_user(factories.admin(2))

	r = client.get(f"/@{user['username']}/info")

	assert_status(r, 200)
	assert (r.json["post_count"], r.json["comment_count"]) == (1, 1)


def test_info_finds_the_user_case_insensitively():
	user = factories.user()

	r = as_user(factories.user()).get(f"/@{user['username'].upper()}/info")

	assert_status(r, 200)
	assert r.json["id"] == user["id"]


@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("ban", ["permanent", "temporary"])
def test_info_of_a_suspended_user(route, ban):
	reason = factories.unique()
	user = factories.user(is_banned=factories.admin(2)["id"], ban_reason=reason, unban_utc=0 if ban == "permanent" else int(time.time()) + 86400)

	r = as_user(factories.user()).get(ROUTES[route](user))

	assert_status(r, 200)
	assert r.json == {
		"username": user["username"],
		"url": f"/@{user['username']}",
		"id": user["id"],
		"is_banned": True,
		"is_permanent_ban": ban == "permanent",
		"ban_reason": reason,
		"post_count": 0,
		"comment_count": 0,
	}


@pytest.mark.parametrize("route", ROUTES)
def test_info_of_a_user_whose_ban_ran_out(route):
	user = factories.user(is_banned=factories.admin(2)["id"], ban_reason=factories.unique(), unban_utc=int(time.time()) - 60)

	r = as_user(factories.user()).get(ROUTES[route](user))

	assert_status(r, 200)
	assert set(r.json) == UNSUSPENDED_KEYS
	assert r.json["is_banned"] is True


@pytest.mark.parametrize("route", ROUTES)
def test_info_refuses_users_the_user_blocks(route):
	user, viewer = factories.user(), factories.user()
	db.insert("userblocks", user_id=user["id"], target_id=viewer["id"])

	r = as_user(viewer).get(ROUTES[route](user))

	assert_status(r, 403)


@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("mutual", [False, True], ids=["one way", "mutual"])
def test_info_refuses_users_who_block_the_user(route, mutual):
	user, viewer = factories.user(), factories.user()
	db.insert("userblocks", user_id=viewer["id"], target_id=user["id"])
	if mutual:
		db.insert("userblocks", user_id=user["id"], target_id=viewer["id"])

	r = as_user(viewer).get(ROUTES[route](user))

	assert_status(r, 403)


def _unknown_user_id():
	return db.execute("SELECT nextval('users_id_seq')")


@pytest.mark.parametrize("path", [lambda: f"/@{factories.unique()}/info", lambda: f"/{_unknown_user_id()}/info", lambda: "/abc/info"], ids=["unknown name", "unknown id", "not a number"])
def test_info_of_an_unknown_user_is_not_found(path):
	r = as_user(factories.user()).get(path())

	assert_status(r, 404)


@pytest.mark.parametrize("route", ROUTES)
def test_info_sends_anonymous_browsers_to_log_in(route):
	path = ROUTES[route](factories.user())

	r = anon().get(path)

	assert_login_redirect(r, path)


# User search answers with the same objects, under the same rule

@pytest.mark.parametrize("hidden", ["private", "shadowbanned"])
def test_user_search_shows_no_activity_of_hidden_users_to_others(hidden):
	user = factories.user(is_private=hidden == "private")
	factories.post(user)
	factories.comment(user, factories.post(factories.user()))
	if hidden == "shadowbanned":
		db.update("users", {"id": user["id"]}, shadowbanned="somemod")

	r = as_api(factories.api_token(factories.user())).get("/search/users", params={"q": user["username"]})

	assert_status(r, 200)
	[found] = [u for u in r.json["data"] if u["id"] == user["id"]]
	assert (found["post_count"], found["comment_count"]) == (0, 0)


def test_user_search_shows_activity_to_the_user_themselves():
	user = factories.user(is_private=True)
	factories.post(user)

	r = as_api(factories.api_token(user)).get("/search/users", params={"q": user["username"]})

	assert_status(r, 200)
	[found] = [u for u in r.json["data"] if u["id"] == user["id"]]
	assert found["post_count"] == 1
