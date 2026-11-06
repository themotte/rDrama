'''
The listings' JSON, for API clients.

- The post listings (the front page, GET /; /changelog; post search, GET /search/posts; a profile's posts, GET /@<username>/posts; the viewer's saved posts, GET /@<username>/saved/posts) hold each listed post's JSON object as the viewer would get it from the post itself (GET /post/<id>), without its replies.
- The comment listings (/comments; comment search, GET /search/comments; a profile's comments, GET /@<username>/; the viewer's saved comments) hold each listed comment's JSON object as the viewer would get it from the comment itself (GET /comment/<id>).
'''
import time

import pytest

from files.tests.spec.harness import *

OLD = int(time.time()) - 2 * 86400


def _listing_path(listing, viewer, post):
	author = db.row("users", id=post["author_id"])
	return {
		"front page": "/",
		"changelog": "/changelog",
		"search": "/search/posts?q=zebra",
		"profile": f"/@{author['username']}/posts",
		"saved": f"/@{viewer['username']}/saved/posts",
	}[listing]


def _post(listing, author, **overrides):
	title = f"[changelog] zebra {factories.unique()}" if listing == "changelog" else f"zebra {factories.unique()}"
	return factories.post(author, title=title, created_utc=OLD, **overrides)


def _listed(listing, viewer, post):
	client = as_api(factories.api_token(viewer))
	r = client.get(_listing_path(listing, viewer, post))
	assert_status(r, 200)
	[listed] = [x for x in r.json["data"] if x["id"] == post["id"]]
	single = client.get(f"/post/{post['id']}").json
	return listed, {k: v for k, v in single.items() if k != "replies"}


LISTINGS = ["front page", "changelog", "search", "profile", "saved"]


@pytest.mark.parametrize("listing", LISTINGS)
def test_a_listed_post_is_its_post_json(listing):
	viewer = factories.user()
	post = _post(listing, factories.admin(1))
	db.insert("save_relationship", user_id=viewer["id"], submission_id=post["id"])

	listed, single = _listed(listing, viewer, post)

	assert listed == single


@pytest.mark.parametrize("listing", LISTINGS)
def test_a_shadowbanned_viewer_sees_their_own_vote_in_listed_scores(listing):
	viewer = factories.user(shadowbanned="somemod")
	post = _post(listing, factories.admin(1))
	factories.vote(viewer, post, 1)
	db.insert("save_relationship", user_id=viewer["id"], submission_id=post["id"])

	listed, single = _listed(listing, viewer, post)

	assert listed == single
	assert listed["upvotes"] == post["upvotes"] + 1


@pytest.mark.parametrize("listing", ["front page", "changelog", "search", "profile"])
def test_authors_get_their_own_hidden_posts_in_full(listing):
	viewer = factories.admin(1)
	post = _post(listing, viewer, state_mod="FILTERED")

	listed, single = _listed(listing, viewer, post)

	assert listed == single
	assert "body_html" in listed


# Comment listings: /comments, comment search (GET /search/comments), a profile's comments (GET /@<username>/) and the viewer's saved comments (GET /@<username>/saved/comments)

COMMENT_LISTINGS = ["comments", "search", "profile", "saved"]


def _comment_listing_path(listing, viewer, comment):
	author = db.row("users", id=comment["author_id"])
	return {
		"comments": "/comments",
		"search": "/search/comments?q=zebra",
		"profile": f"/@{author['username']}/",
		"saved": f"/@{viewer['username']}/saved/comments",
	}[listing]


def _listed_comment(listing, viewer, comment):
	client = as_api(factories.api_token(viewer))
	r = client.get(_comment_listing_path(listing, viewer, comment))
	assert_status(r, 200)
	[listed] = [x for x in r.json["data"] if x["id"] == comment["id"]]
	return listed, client.get(f"/comment/{comment['id']}").json


@pytest.mark.parametrize("listing", COMMENT_LISTINGS)
def test_a_listed_comments_post_is_hidden_from_viewers_blocking_its_author(listing):
	viewer = factories.user()
	post_author = factories.user()
	db.insert("userblocks", user_id=viewer["id"], target_id=post_author["id"])
	post = factories.post(post_author, created_utc=OLD)
	comment = factories.comment(factories.user(), post, body=f"zebra {factories.unique()}", created_utc=OLD)
	db.insert("comment_save_relationship", user_id=viewer["id"], comment_id=comment["id"])

	listed, single = _listed_comment(listing, viewer, comment)

	assert "body_html" not in single["post"]
	assert listed == single
