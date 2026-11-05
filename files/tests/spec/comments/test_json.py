'''
The JSON object of a visible comment, as API clients get it from the comment's own page (GET /comment/<comment id>) and, without "author" and "post", nested in other objects (a post's "replies" at GET /post/<post id>, a comment's "replies").

It has "id", "level" (1 for a top-level comment, one more than its parent's for a reply), "author_name", "body" (the source text), "body_html", "is_bot", "created_utc", "edited_utc" (0 if never edited), "is_nsfw" (the comment is 18+), "permalink" ("/comment/<id>"), "is_pinned" (who pinned it, or null), "distinguish_level", "post_id" and "replies" (the replies' objects, newest first by default). Replies add "parent_comment_id". "score", "upvotes" and "downvotes" are left out while the comment is younger than a day. The object at the top of a response adds "author" (the author's public details, as in GET /@<username>/info without the counts) and "post" (the post's object). On posts where authors are anonymous, "author_name" and "author" are "👻" instead.

The JSON follows what the viewer may see. A comment hidden from them (removed, held, deleted, by a shadowbanned user, or by a user they block, as on the page) is a stub: "id", "post", "level", "parent", "replies" and, as the page tells, who removed it ("state_mod_set_by"; null for a shadowbanned user's comment, as for one removed by no one named) or when its author deleted it ("state_user_deleted_utc"), without its text or author. Its author and moderators get the whole object. The "post" in a comment's object is the post as the viewer may see it, without its replies.
'''
import time

import pytest

from files.tests.spec.harness import *

AUTHOR_KEYS = {"username", "url", "id", "is_banned", "created_utc", "is_private", "profile_url", "bannerurl", "bio", "bio_html", "flair"}


def _api():
	return as_api(factories.api_token(factories.user()))


def _expected(comment, writer, on_post, **extra):
	return {
		"id": comment["id"],
		"level": comment["level"],
		"author_name": writer["username"],
		"body": comment["body"],
		"body_html": comment["body_html"],
		"is_bot": False,
		"created_utc": comment["created_utc"],
		"edited_utc": 0,
		"is_nsfw": False,
		"permalink": f"/comment/{comment['id']}",
		"is_pinned": None,
		"distinguish_level": 0,
		"post_id": on_post["id"],
		"score": 1,
		"upvotes": 1,
		"downvotes": 0,
		"replies": [],
		**extra,
	}


def test_api_clients_get_the_comment_as_json():
	author = factories.user()
	post = factories.post(factories.user())
	comment = factories.comment(author, post, body="hello", body_html="<p>hello</p>", created_utc=1000)

	r = _api().get(f"/comment/{comment['id']}")

	assert_status(r, 200)
	assert r.json == _expected(comment, author, post, author=ANY, post=ANY)
	assert set(r.json["author"]) == AUTHOR_KEYS
	assert (r.json["author"]["id"], r.json["author"]["username"]) == (author["id"], author["username"])
	assert r.json["post"]["id"] == post["id"]


def test_comment_json_carries_its_markings():
	post = factories.post(factories.user())
	author = factories.admin(2)
	comment = factories.comment(author, post, created_utc=1000, edited_utc=2000, over_18=True, is_bot=True, is_pinned="somemod", distinguish_level=1, upvotes=5, downvotes=2)

	r = _api().get(f"/comment/{comment['id']}")

	assert_status(r, 200)
	assert {k: r.json[k] for k in ["edited_utc", "is_nsfw", "is_bot", "is_pinned", "distinguish_level", "score", "upvotes", "downvotes"]} == {
		"edited_utc": 2000,
		"is_nsfw": True,
		"is_bot": True,
		"is_pinned": "somemod",
		"distinguish_level": 1,
		"score": 3,
		"upvotes": 5,
		"downvotes": 2,
	}


def test_replies_are_nested_with_their_parent():
	post = factories.post(factories.user())
	top_author, reply_author, deeper_author = factories.user(), factories.user(), factories.user()
	top = factories.comment(top_author, post, created_utc=1000)
	reply = factories.comment(reply_author, post, parent=top, created_utc=1100)
	deeper = factories.comment(deeper_author, post, parent=reply, created_utc=1200)

	r = _api().get(f"/comment/{top['id']}")

	assert_status(r, 200)
	assert r.json["replies"] == [_expected(reply, reply_author, post, parent_comment_id=top["id"], replies=[
		_expected(deeper, deeper_author, post, parent_comment_id=reply["id"]),
	])]


def test_replies_are_newest_first():
	post = factories.post(factories.user())
	top = factories.comment(factories.user(), post, created_utc=1000)
	older = factories.comment(factories.user(), post, parent=top, created_utc=1100)
	newer = factories.comment(factories.user(), post, parent=top, created_utc=1200)

	r = _api().get(f"/comment/{top['id']}")

	assert_status(r, 200)
	assert [c["id"] for c in r.json["replies"]] == [newer["id"], older["id"]]


def test_a_reply_on_its_own_names_its_parent():
	post = factories.post(factories.user())
	top = factories.comment(factories.user(), post, created_utc=1000)
	author = factories.user()
	reply = factories.comment(author, post, parent=top, created_utc=1100)

	r = _api().get(f"/comment/{reply['id']}")

	assert_status(r, 200)
	assert r.json == _expected(reply, author, post, parent_comment_id=top["id"], author=ANY, post=ANY)


def test_young_comments_leave_out_their_scores():
	post = factories.post(factories.user())
	comment = factories.comment(factories.user(), post, created_utc=int(time.time()) - 3600)

	r = _api().get(f"/comment/{comment['id']}")

	assert_status(r, 200)
	assert not {"score", "upvotes", "downvotes"} & set(r.json)


def test_comments_older_than_a_day_have_their_scores():
	post = factories.post(factories.user())
	comment = factories.comment(factories.user(), post, created_utc=int(time.time()) - 86400 - 60)

	r = _api().get(f"/comment/{comment['id']}")

	assert_status(r, 200)
	assert (r.json["score"], r.json["upvotes"], r.json["downvotes"]) == (1, 1, 0)


def test_post_json_nests_its_comments_without_author_or_post():
	post = factories.post(factories.user())
	top_author, reply_author = factories.user(), factories.user()
	top = factories.comment(top_author, post, created_utc=1000)
	reply = factories.comment(reply_author, post, parent=top, created_utc=1100)

	r = _api().get(f"/post/{post['id']}")

	assert_status(r, 200)
	assert r.json["replies"] == [_expected(top, top_author, post, replies=[
		_expected(reply, reply_author, post, parent_comment_id=top["id"]),
	])]


def test_comments_on_anonymous_posts_hide_their_author():
	author = factories.user()
	post = factories.post(factories.user(), ghost=True)
	comment = factories.comment(author, post, created_utc=1000)

	r = _api().get(f"/comment/{comment['id']}")

	assert_status(r, 200)
	assert (r.json["author_name"], r.json["author"]) == ("👻", "👻")
	assert_not_in_payload(r, author["username"])



def _blocking_api(viewer, blocked):
	db.insert("userblocks", user_id=viewer["id"], target_id=blocked["id"])
	return as_api(factories.api_token(viewer))


def test_comments_by_users_the_viewer_blocks_are_stubs():
	viewer, author = factories.user(), factories.user()
	comment = factories.comment(author, factories.post(factories.user()), body=factories.unique())

	r = _blocking_api(viewer, author).get(f"/comment/{comment['id']}")

	assert_status(r, 200)
	assert_not_in_payload(r, comment["body"])
	assert r.json["id"] == comment["id"]


def test_post_json_shows_comments_by_users_the_viewer_blocks_as_stubs():
	viewer, author = factories.user(), factories.user()
	post = factories.post(factories.user())
	comment = factories.comment(author, post, body=factories.unique())

	r = _blocking_api(viewer, author).get(f"/post/{post['id']}")

	assert_status(r, 200)
	assert_not_in_payload(r, comment["body"])
	assert [c["id"] for c in r.json["replies"]] == [comment["id"]]


def test_authors_get_their_own_removed_comment_whole():
	author = factories.user()
	comment = factories.comment(author, factories.post(factories.user()), body=factories.unique(), state_mod="REMOVED", state_mod_set_by="somemod")

	r = as_api(factories.api_token(author)).get(f"/comment/{comment['id']}")

	assert_status(r, 200)
	assert r.json["body"] == comment["body"]


def test_the_post_in_a_comments_json_is_as_the_viewer_may_see_it():
	viewer, op = factories.user(), factories.user()
	post = factories.post(op, body=factories.unique())
	comment = factories.comment(factories.user(), post)

	r = _blocking_api(viewer, op).get(f"/comment/{comment['id']}")

	assert_status(r, 200)
	assert_not_in_payload(r, post["body"])
	assert r.json["post"]["id"] == post["id"]
	assert "replies" not in r.json["post"]


def test_new_comments_json_has_the_post_as_the_viewer_may_see_it():
	viewer, op = factories.user(), factories.user()
	post = factories.post(op, body=factories.unique())
	client = _blocking_api(viewer, op)

	r = client.post("/comment", {"parent_fullname": f"post_{post['id']}", "body": factories.unique()})

	assert_status(r, 200)
	assert_not_in_payload(r, post["body"])
	assert r.json["post"]["id"] == post["id"]


def test_a_shadowbanned_users_own_comments_are_whole_to_them_in_search():
	author = factories.user(shadowbanned="somemod")
	token = factories.unique()
	factories.comment(author, factories.post(factories.user()), body=f"words {token}")

	r = as_api(factories.api_token(author)).get("/search/comments", params={"q": token})

	assert_status(r, 200)
	assert_in_payload(r, token)


@pytest.mark.parametrize("viewer", ["user", "the reply's author"])
def test_replies_in_a_listed_comments_json_follow_the_shadowban_rule(viewer):
	author, replier = factories.user(), factories.user(shadowbanned="somemod")
	comment = factories.comment(author, factories.post(factories.user()))
	reply = factories.comment(replier, db.row("submissions", id=comment["parent_submission"]), parent=comment, body=factories.unique())
	client = as_api(factories.api_token(replier if viewer == "the reply's author" else factories.user()))

	r = client.get(f"/@{author['username']}/")

	assert_status(r, 200)
	(assert_in_payload if viewer == "the reply's author" else assert_not_in_payload)(r, reply["body"])


def test_a_shadowbanned_users_stub_looks_like_a_removed_one():
	post = factories.post(factories.user())
	hidden = factories.comment(factories.user(shadowbanned="somemod"), post)
	factories.comment(factories.user(), post, parent=hidden)

	r = _api().get(f"/post/{post['id']}")

	assert_status(r, 200)
	[stub] = r.json["replies"]
	assert stub["id"] == hidden["id"] and stub["state_mod_set_by"] is None and "body" not in stub
