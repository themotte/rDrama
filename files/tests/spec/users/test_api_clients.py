'''
API clients act without admin powers. A request authenticated by an access token is treated as coming from a user with no admin level, whatever the account's level: it sees only what non-admins see, can't act on other users' content, and is held to the rules admins are exempt from (new posts held for review under FilterNewPosts, changes refused in read-only mode). Admin pages refuse API clients outright (see the admin area).

The one exception is the check that shadowbans accounts flagged as evading a ban, which judges the account by its real level: an admin's account is never shadowbanned because a token was used.

What an admin sees in the browser never leaks to the same admin's API client, nor the reverse.
'''
from files.tests.spec.harness import *


def test_api_clients_of_admins_cant_see_private_profiles():
	owner = factories.user(is_private=True)
	factories.post(owner)

	r = as_api(factories.api_token(factories.admin(2))).get(f"/@{owner['username']}/posts")

	assert_status(r, 403)


def test_api_clients_of_admins_dont_see_others_deleted_comments():
	author = factories.user()
	visible = factories.comment(author, factories.post(factories.user()))
	deleted = factories.comment(author, factories.post(factories.user()), state_user_deleted_utc="2020-01-01T00:00:00Z")

	r = as_api(factories.api_token(factories.admin(2))).get(f"/@{author['username']}/")

	assert_status(r, 200)
	assert [c["id"] for c in r.json["data"]] == [visible["id"]]


def test_an_admins_browser_view_doesnt_reach_their_api_client():
	author, admin = factories.user(), factories.admin(2)
	visible = factories.post(author)
	factories.post(author, private=True)
	assert_html(as_user(admin).get(f"/@{author['username']}/posts"), 200)

	r = as_api(factories.api_token(admin)).get(f"/@{author['username']}/posts")

	assert_status(r, 200)
	assert [p["id"] for p in r.json["data"]] == [visible["id"]]


def test_an_admins_api_client_view_doesnt_reach_their_browser():
	author, admin = factories.user(), factories.admin(2)
	factories.post(author)
	draft = factories.post(author, private=True, title=factories.unique())
	assert_status(as_api(factories.api_token(admin)).get(f"/@{author['username']}/posts"), 200)

	r = as_user(admin).get(f"/@{author['username']}/posts")

	assert_html(r, 200)
	assert_in_payload(r, draft["title"])


def test_api_clients_of_admins_are_refused_changes_in_read_only_mode():
	admin = factories.admin(3, cardview=False)
	client = as_api(factories.api_token(admin))
	site_settings_set("Read-only mode", True)

	with db_diff() as d:
		r = client.post("/settings/profile", {"cardview": "true"})

	assert_status(r, 403)
	d.assert_exactly()


def test_api_clients_of_admins_cant_edit_others_posts():
	post = factories.post(factories.user(), body="before")
	client = as_api(factories.api_token(factories.admin(3)))

	with db_diff() as d:
		r = client.post(f"/edit_post/{post['id']}", {"title": post["title"], "body": "after"})

	assert_status(r, 403)
	d.assert_exactly()


def test_api_clients_of_admins_have_new_posts_held_for_review():
	site_settings_set("FilterNewPosts", True)
	author = factories.admin(2)
	client = as_api(factories.api_token(author))

	with db_diff() as d:
		r = client.post("/submit", {"title": factories.unique("title"), "body": factories.unique("body")})

	assert_status(r, 200)
	d.assert_exactly(inserted={"submissions": [{"state_mod": "FILTERED"}], "votes": [{"user_id": author["id"]}]})


def test_api_clients_of_admins_flagged_for_ban_evasion_are_not_shadowbanned():
	admin = factories.admin(2, ban_evade=1)
	client = as_api(factories.api_token(admin))

	with db_diff() as d:
		r = client.get(f"/@{admin['username']}/info")

	assert_status(r, 200)
	d.assert_exactly()
