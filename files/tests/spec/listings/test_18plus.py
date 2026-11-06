'''
18+ posts in the post listings (the front page, /changelog, post search, a profile's posts, saved posts) and the site's feed (GET /rss).

A viewer who hasn't confirmed they are 18 or over (one without the 18+ setting, "over_18", and not having confirmed on a post's page) gets a listed 18+ post with its title and 18+ mark only: its text, its link and anything embedded from it are left out of the page. For API clients its JSON object then holds only "id", "title", "permalink", "state_mod_set_by", "state_user_deleted_utc" and "is_nsfw" (true). The feed, read without logging in, never holds an 18+ post's text.

Viewers who have the 18+ setting get 18+ posts like any other.
'''
import time

import pytest

from files.tests.spec.harness import *

OLD = int(time.time()) - 2 * 86400


def _post(listing, author, **overrides):
	title = f"[changelog] zebra {factories.unique()}" if listing == "changelog" else f"zebra {factories.unique()}"
	return factories.post(author, title=title, created_utc=OLD, over_18=True, **overrides)


def _path(listing, viewer, post):
	author = db.row("users", id=post["author_id"])
	return {
		"front page": "/",
		"changelog": "/changelog",
		"search": "/search/posts?q=zebra",
		"profile": f"/@{author['username']}/posts",
		"saved": f"/@{viewer['username']}/saved/posts",
	}[listing]


LISTINGS = ["front page", "changelog", "search", "profile", "saved"]


def _arrange(listing, over_18, **overrides):
	viewer = factories.user(over_18=over_18)
	post = _post(listing, factories.admin(1), **overrides)
	db.insert("save_relationship", user_id=viewer["id"], submission_id=post["id"])
	return viewer, post


@pytest.mark.parametrize("listing", LISTINGS)
@pytest.mark.parametrize("over_18", [False, True])
def test_an_18_plus_posts_text_is_listed_only_for_18_plus_viewers(listing, over_18):
	body = factories.unique()
	viewer, post = _arrange(listing, over_18, body=body)

	r = as_user(viewer).get(_path(listing, viewer, post))

	assert_html(r, 200)
	assert_in_payload(r, post["title"])
	(assert_in_payload if over_18 else assert_not_in_payload)(r, body)


@pytest.mark.parametrize("listing", LISTINGS)
@pytest.mark.parametrize("kind", ["link", "image", "video"])
@pytest.mark.parametrize("over_18", [False, True])
def test_an_18_plus_posts_link_is_listed_only_for_18_plus_viewers(listing, kind, over_18):
	token = factories.unique()
	url = {"link": f"https://example.com/{token}", "image": f"https://example.com/{token}.png", "video": f"https://example.com/{token}.mp4"}[kind]
	viewer, post = _arrange(listing, over_18, url=url)

	r = as_user(viewer).get(_path(listing, viewer, post))

	assert_in_payload(r, post["title"])
	(assert_in_payload if over_18 else assert_not_in_payload)(r, token)


@pytest.mark.parametrize("viewer", ["visitor", "user"])
def test_confirming_age_lists_18_plus_text(viewer):
	body = factories.unique()
	post = _post("front page", factories.user(), body=body)
	client = anon() if viewer == "visitor" else as_user(factories.user(over_18=False))

	assert_redirect(client.post("/allow_nsfw", {"redir": "/"}), "/")
	r = client.get("/")

	assert_in_payload(r, body)


def test_logged_out_visitors_get_no_18_plus_text():
	body = factories.unique()
	post = _post("front page", factories.user(), body=body)

	r = anon().get("/")

	assert_in_payload(r, post["title"])
	assert_not_in_payload(r, body)


@pytest.mark.parametrize("listing", LISTINGS)
def test_api_clients_without_the_setting_get_only_the_posts_identity(listing):
	viewer, post = _arrange(listing, False, body=factories.unique())

	r = as_api(factories.api_token(viewer)).get(_path(listing, viewer, post))

	[listed] = [x for x in r.json["data"] if x["id"] == post["id"]]
	assert set(listed) == {"id", "title", "permalink", "state_mod_set_by", "state_user_deleted_utc", "is_nsfw"}
	assert listed["is_nsfw"] is True and listed["title"] == post["title"]


@pytest.mark.parametrize("listing", LISTINGS)
def test_api_clients_with_the_setting_get_the_whole_post(listing):
	viewer, post = _arrange(listing, True, body=factories.unique())
	client = as_api(factories.api_token(viewer))

	[listed] = [x for x in client.get(_path(listing, viewer, post)).json["data"] if x["id"] == post["id"]]

	assert listed == {k: v for k, v in client.get(f"/post/{post['id']}").json.items() if k != "replies"}


def test_the_feed_leaves_out_18_plus_text():
	body, other_body = factories.unique(), factories.unique()
	post = _post("front page", factories.user(), body=body)
	other = factories.post(factories.user(), body=other_body)

	r = anon().get("/rss")

	assert_status(r, 200)
	assert_in_payload(r, post["title"])
	assert_not_in_payload(r, body)
	assert_in_payload(r, other_body)
