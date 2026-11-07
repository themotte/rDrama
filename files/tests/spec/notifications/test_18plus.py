'''
Notifications of comments on 18+ posts are shown as comment listings show them (listings/test_18plus): to viewers who haven't confirmed their age (neither 18+ users nor confirmed through POST /allow_nsfw), the post's title and the 18+ tag, but not the comment; in JSON (/notifications and /unread), only the comment's place and "is_nsfw". Comments marked 18+ on other posts are shown like any other.
'''
import pytest

from files.tests.spec.harness import *


def _notified(viewer, post_over_18=True, comment_over_18=True):
	post = factories.post(viewer, over_18=post_over_18)
	reply = factories.comment(factories.user(), post, parent=factories.comment(viewer, post), over_18=comment_over_18)
	factories.notification(viewer, reply)
	return reply, post


@pytest.mark.parametrize("over_18", [False, True])
def test_the_comment_shows_only_to_18_plus_viewers(over_18):
	viewer = factories.user(over_18=over_18)
	reply, post = _notified(viewer)

	r = as_user(viewer).get("/notifications")

	assert_html(r, 200)
	assert_in_payload(r, post["title"])
	(assert_in_payload if over_18 else assert_not_in_payload)(r, reply["body"])


def test_confirming_age_shows_the_comment():
	viewer = factories.user(over_18=False)
	reply, _ = _notified(viewer)
	client = as_user(viewer)
	client.post("/allow_nsfw", {"redir": "/"})

	assert_in_payload(client.get("/notifications"), reply["body"])


def test_18_plus_comments_on_other_posts_show_like_any_other():
	viewer = factories.user(over_18=False)
	reply, _ = _notified(viewer, post_over_18=False)

	assert_in_payload(as_user(viewer).get("/notifications"), reply["body"])


@pytest.mark.parametrize("path", ["/notifications", "/unread"])
def test_api_clients_without_the_setting_get_a_stub(path):
	viewer = factories.user(over_18=False)
	reply, post = _notified(viewer, comment_over_18=False)

	r = as_api(factories.api_token(viewer)).get(path)

	assert r.json["data"] == [{"id": reply["id"], "post": post["id"], "level": 2, "parent": f"comment_{reply['parent_comment_id']}", "replies": [], "is_nsfw": True}]


@pytest.mark.parametrize("path", ["/notifications", "/unread"])
def test_api_clients_with_the_setting_get_the_comment(path):
	viewer = factories.user(over_18=True)
	reply, _ = _notified(viewer)

	[item] = as_api(factories.api_token(viewer)).get(path).json["data"]

	assert item["id"] == reply["id"] and reply["body"] in item["body_html"]


def test_messages_are_never_stubs():
	viewer = factories.user(over_18=False)
	message = factories.message(factories.user(), viewer, over_18=True)
	factories.notification(viewer, message)

	[item] = as_api(factories.api_token(viewer)).get("/notifications").json["data"]

	assert message["text"] in item["body_html"]
