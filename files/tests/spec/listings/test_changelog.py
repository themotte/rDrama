'''
GET /changelog lists the changelog posts, for logged-in users only (others are sent to log in).

A changelog post is a post by an admin (level 1 and up) whose title starts with "[changelog]" or "(changelog)", in any letter case. The listing takes "page", "sort" and "t" as the front page does (test_front), 25 posts to a page, newest first by default. Removed and filtered changelog posts, deleted ones and drafts are left out, as are those by users the viewer blocks.

The front page leaves changelog posts out unless the viewer subscribes (test_front).

An API client gets {"data": [...], "next_exists": ...}, as from the front page.
'''
import time

import pytest

from files.tests.spec.harness import *

NOW = int(time.time())


def _changelog(prefix="[changelog]", author=None, **overrides):
	sentinel = factories.unique()
	post = factories.post(author or factories.admin(1), title=f"{prefix} {sentinel}", **overrides)
	return {**post, "sentinel": sentinel}


def test_logged_out_visitors_are_sent_to_log_in():
	assert_login_redirect(anon().get("/changelog"), "/changelog")


@pytest.mark.parametrize("prefix", ["[changelog]", "(changelog)", "[Changelog]", "(CHANGELOG)"])
def test_admins_changelog_posts_are_listed(prefix):
	post = _changelog(prefix)

	r = as_user(factories.user()).get("/changelog")

	assert_html(r, 200)
	assert_in_payload(r, post["sentinel"])


@pytest.mark.parametrize("level", [1, 2, 3])
def test_changelog_posts_by_every_admin_level_are_listed(level):
	post = _changelog(author=factories.admin(level))

	r = as_user(factories.user()).get("/changelog")

	assert_in_payload(r, post["sentinel"])


def test_changelog_titled_posts_by_others_are_not_listed():
	post = _changelog(author=factories.user())

	r = as_user(factories.user()).get("/changelog")

	assert_not_in_payload(r, post["sentinel"])


def test_other_posts_by_admins_are_not_listed():
	post = factories.post(factories.admin(3))

	r = as_user(factories.user()).get("/changelog")

	assert_not_in_payload(r, post["title"])


@pytest.mark.parametrize("state", [
	{"state_mod": "REMOVED", "state_mod_set_by": "somemod"},
	{"state_mod": "FILTERED"},
	{"state_user_deleted_utc": "2020-01-01T00:00:00Z"},
	{"private": True},
])
def test_hidden_changelog_posts_are_left_out(state):
	post = _changelog(**state)

	r = as_user(factories.user()).get("/changelog")

	assert_not_in_payload(r, post["sentinel"])


@pytest.mark.parametrize("state", [{"state_user_deleted_utc": "2020-01-01T00:00:00Z"}, {"private": True}])
def test_deleted_changelog_posts_and_drafts_are_left_out_for_admins_too(state):
	post = _changelog(**state)

	r = as_user(factories.admin(3)).get("/changelog")

	assert_not_in_payload(r, post["sentinel"])


def test_changelog_posts_by_blocked_admins_are_left_out():
	author = factories.admin(1)
	viewer = factories.user()
	db.insert("userblocks", user_id=viewer["id"], target_id=author["id"])
	post = _changelog(author=author)

	r = as_user(viewer).get("/changelog")

	assert_not_in_payload(r, post["sentinel"])


def test_newest_first_by_default():
	older = _changelog(created_utc=NOW - 7200)
	newer = _changelog(created_utc=NOW - 60)

	r = as_user(factories.user()).get("/changelog")

	assert_in_order(r, [newer["sentinel"], older["sentinel"]])


def test_sort_and_time_filter_apply():
	old = _changelog(created_utc=NOW - 7200)
	older = _changelog(created_utc=NOW - 3 * 86400)
	recent = _changelog(created_utc=NOW - 60)

	r = as_user(factories.user()).get("/changelog", params={"sort": "old", "t": "day"})

	assert_in_order(r, [old["sentinel"], recent["sentinel"]])
	assert_not_in_payload(r, older["sentinel"])


def test_pages_hold_25():
	posts = [_changelog(created_utc=NOW - 60 * (i + 1)) for i in range(26)]
	client = as_user(factories.user())

	first, second = client.get("/changelog"), client.get("/changelog", params={"page": 2})

	assert_in_payload(first, posts[24]["sentinel"])
	assert_not_in_payload(first, posts[25]["sentinel"])
	assert_in_payload(second, posts[25]["sentinel"])
	assert_not_in_payload(second, posts[24]["sentinel"])


def test_api_clients_get_json():
	posts = [_changelog(created_utc=NOW - 60 * (i + 1)) for i in range(26)]

	r = as_api(factories.api_token(factories.user())).get("/changelog")

	assert_status(r, 200)
	assert set(r.json) == {"data", "next_exists"}
	assert [p["id"] for p in r.json["data"]] == [p["id"] for p in posts[:25]]
	assert r.json["next_exists"] is True
