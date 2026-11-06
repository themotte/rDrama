'''
Every listing shows the site as it is at the request: whatever changed since an earlier request (votes, comments, the viewer's settings, blocks and admin level) shows on the next one.
'''
import time

from files.tests.spec.harness import *

NOW = int(time.time())


def test_a_vote_reorders_the_front_page_at_once():
	first = factories.post(factories.user(), created_utc=NOW - 60)
	second = factories.post(factories.user(), created_utc=NOW - 7200)
	client = as_user(factories.user())
	assert_in_order(client.get("/", params={"sort": "top"}), [first["title"], second["title"]])

	factories.vote(factories.user(), second, 1)

	assert_in_order(client.get("/", params={"sort": "top"}), [second["title"], first["title"]])


def test_a_new_comment_reorders_the_front_page_at_once():
	first = factories.post(factories.user(), created_utc=NOW - 60)
	second = factories.post(factories.user(), created_utc=NOW - 7200)
	client = anon()
	assert_in_order(client.get("/", params={"sort": "comments"}), [first["title"], second["title"]])

	factories.comment(factories.user(), second)

	assert_in_order(client.get("/", params={"sort": "comments"}), [second["title"], first["title"]])


def test_hiding_voted_posts_applies_at_once():
	viewer = factories.user()
	voted = factories.post(factories.user())
	factories.vote(viewer, voted, 1)
	client = as_user(viewer)
	assert_in_payload(client.get("/"), voted["title"])

	assert_json_message(client.post("/settings/profile", {"hidevotedon": "true"}))

	assert_not_in_payload(client.get("/"), voted["title"])


def test_a_new_admin_level_applies_at_once():
	viewer = factories.user()
	removed = factories.post(factories.user(), state_mod="REMOVED", state_mod_set_by="somemod")
	client = as_user(viewer)
	assert_not_in_payload(client.get("/"), removed["title"])

	db.update("users", {"id": viewer["id"]}, admin_level=2)

	assert_in_payload(client.get("/"), removed["title"])


def test_blocking_an_author_applies_to_the_changelog_at_once():
	author = factories.admin(1)
	post = factories.post(author, title=f"[changelog] {factories.unique()}")
	client = as_user(factories.user())
	assert_in_payload(client.get("/changelog"), post["title"])

	assert_json_message(client.post("/settings/block", {"username": author["username"]}))

	assert_not_in_payload(client.get("/changelog"), post["title"])


def test_a_vote_reorders_a_profile_at_once():
	author = factories.user()
	first = factories.post(author, created_utc=NOW - 60)
	second = factories.post(author, created_utc=NOW - 7200)
	client = anon()
	assert_in_order(client.get(f"/@{author['username']}/posts", params={"sort": "top"}), [first["title"], second["title"]])

	factories.vote(factories.user(), second, 1)

	assert_in_order(client.get(f"/@{author['username']}/posts", params={"sort": "top"}), [second["title"], first["title"]])
