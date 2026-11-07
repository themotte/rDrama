'''
The notification pages, for logged-in users (visitors are sent to log in; API clients get the same pages as JSON).

GET /notifications lists what the user was notified of, newest notification first: replies, mentions, messages and the site's own notices. Each shows alone, without its replies. Left out:
- comments that were removed, are held for approval (filtered) or deleted;
- comments by users the viewer blocks, except messages from admins from level 2 (who may message users blocking them, test_messages);
- comments by shadowbanned users, except to admins from level 2 (shadowbanned users don't see each other's);
- notifications of followed users' new posts, which have their own page.
Showing a notification marks it read.

GET /notifications/posts lists notifications of followed users' new posts, newest first, marking them read.

GET /notifications/messages lists the conversations the user sent or received (their first messages, newest first), each with its replies. Left out: conversations started by users the viewer blocks (except admins from level 2), and by shadowbanned users, except to the users themselves and admins from level 2.

Each page holds 25; "page" (from 1) chooses it. API clients get {"data": [...]}, the page's comments as JSON objects.

Modmail's page is in test_modmail.
'''
import pytest

from files.tests.spec.harness import *

PAGES = ["/notifications", "/notifications/posts", "/notifications/messages"]


def _notified_reply(user, **overrides):
	'''A reply to `user`'s comment, of which they were notified.'''
	post = factories.post(user)
	reply = factories.comment(overrides.pop("author", None) or factories.user(), post, parent=factories.comment(user, post), **overrides)
	factories.notification(user, reply)
	return reply


def _new_post_notification(user):
	'''A notification, from AutoJanny, of a followed user's new post.'''
	notice = factories.message(db.row("users", id=seed.AUTOJANNY_ID), None, distinguish_level=6)
	factories.notification(user, notice)
	return notice


def _notice(user):
	'''One of the site's own notices, from the system account.'''
	notice = factories.message(db.row("users", id=seed.SYSTEM_ID), None, distinguish_level=6)
	factories.notification(user, notice)
	return notice


@pytest.mark.parametrize("path", PAGES)
def test_logged_out_visitors_are_sent_to_log_in(path):
	assert_login_redirect(anon().get(path), path)


# /notifications

def test_lists_notifications_newest_first():
	user = factories.user()
	older, newer = _notified_reply(user), _notified_reply(user)
	db.execute("UPDATE notifications SET created_datetimez = now() - interval '1 hour' WHERE comment_id = :id", id=older["id"])

	r = as_user(user).get("/notifications")

	assert_html(r, 200)
	assert_in_order(r, [newer["body"], older["body"]])


def test_lists_messages_and_notices():
	user = factories.user()
	message = factories.message(factories.user(), user)
	factories.notification(user, message)
	notice = _notice(user)

	r = as_user(user).get("/notifications")

	assert_in_payload(r, message["text"])
	assert_in_payload(r, notice["text"])


def test_notifications_show_without_their_replies():
	user = factories.user()
	reply = _notified_reply(user)
	answer = factories.comment(factories.user(), db.row("submissions", id=reply["parent_submission"]), parent=reply)

	r = as_user(user).get("/notifications")

	assert_in_payload(r, reply["body"])
	assert_not_in_payload(r, answer["body"])


def test_only_the_viewers_own_notifications():
	user = factories.user()
	someone_elses = _notified_reply(factories.user())

	assert_not_in_payload(as_user(user).get("/notifications"), someone_elses["body"])


def test_showing_notifications_marks_them_read():
	user = factories.user()
	reply = _notified_reply(user)
	client = as_user(user)

	with db_diff() as d:
		client.get("/notifications")

	d.assert_exactly(updated={"notifications": {(user["id"], reply["id"]): {"read": True}}})


def test_read_notifications_still_show():
	user = factories.user()
	reply = _notified_reply(user)
	db.update("notifications", {"user_id": user["id"], "comment_id": reply["id"]}, read=True)

	assert_in_payload(as_user(user).get("/notifications"), reply["body"])


@pytest.mark.parametrize("state", [{"state_mod": "REMOVED"}, {"state_mod": "FILTERED"}, {"state_user_deleted_utc": "2020-01-01T00:00:00Z"}], ids=["removed", "filtered", "deleted"])
@pytest.mark.parametrize("viewer", ["user", "admin"])
def test_hidden_comments_are_left_out(state, viewer):
	user = factories.user() if viewer == "user" else factories.admin(3)
	reply = _notified_reply(user, **state)

	assert_not_in_payload(as_user(user).get("/notifications"), reply["body"])


@pytest.mark.parametrize("viewer", ["user", "admin"])
def test_blocked_authors_are_left_out(viewer):
	user = factories.user() if viewer == "user" else factories.admin(3)
	author = factories.user()
	reply = _notified_reply(user, author=author)
	db.insert("userblocks", user_id=user["id"], target_id=author["id"])

	assert_not_in_payload(as_user(user).get("/notifications"), reply["body"])


@pytest.mark.parametrize("level", [2, 3])
def test_messages_from_blocked_admins_show(level):
	user, admin = factories.user(), factories.admin(level)
	message = factories.message(admin, user)
	factories.notification(user, message)
	db.insert("userblocks", user_id=user["id"], target_id=admin["id"])

	assert_in_payload(as_user(user).get("/notifications"), message["text"])
	assert_in_payload(as_user(user).get("/notifications/messages"), message["text"])
	assert_in_payload(as_user(user).get(f"/comment/{message['id']}"), message["text"])


def test_comments_by_blocked_admins_are_left_out():
	user, admin = factories.user(), factories.admin(3)
	reply = _notified_reply(user, author=admin)
	db.insert("userblocks", user_id=user["id"], target_id=admin["id"])

	assert_not_in_payload(as_user(user).get("/notifications"), reply["body"])


def test_messages_from_blocked_level_1_admins_are_left_out():
	user, admin = factories.user(), factories.admin(1)
	message = factories.message(admin, user)
	factories.notification(user, message)
	db.insert("userblocks", user_id=user["id"], target_id=admin["id"])

	assert_not_in_payload(as_user(user).get("/notifications"), message["text"])
	assert_not_in_payload(as_user(user).get("/notifications/messages"), message["text"])


def test_authors_who_block_the_viewer_still_show():
	user, author = factories.user(), factories.user()
	reply = _notified_reply(user, author=author)
	db.insert("userblocks", user_id=author["id"], target_id=user["id"])

	assert_in_payload(as_user(user).get("/notifications"), reply["body"])


def test_shadowbanned_authors_are_left_out_for_users():
	user = factories.user()
	reply = _notified_reply(user, author=factories.user(shadowbanned="somemod"))

	assert_not_in_payload(as_user(user).get("/notifications"), reply["body"])


@pytest.mark.parametrize("level", [2, 3])
def test_shadowbanned_authors_show_to_admins_from_level_2(level):
	admin = factories.admin(level)
	reply = _notified_reply(admin, author=factories.user(shadowbanned="somemod"))

	assert_in_payload(as_user(admin).get("/notifications"), reply["body"])


def test_shadowbanned_users_dont_see_each_others_comments():
	user = factories.user(shadowbanned="somemod")
	_notified_reply(user, author=factories.user(shadowbanned="somemod"))

	r = as_api(factories.api_token(user)).get("/notifications")

	assert r.json["data"] == []


def test_new_post_notifications_are_left_out():
	user = factories.user()
	notice = _new_post_notification(user)

	assert_not_in_payload(as_user(user).get("/notifications"), notice["text"])


def test_pages_hold_25():
	user = factories.user()
	replies = [_notified_reply(user) for _ in range(26)]
	db.execute("UPDATE notifications SET created_datetimez = now() - interval '1 hour' WHERE comment_id = :id", id=replies[0]["id"])
	client = as_user(user)

	first, second = client.get("/notifications"), client.get("/notifications", params={"page": 2})

	assert_in_payload(first, replies[25]["body"])
	assert_not_in_payload(first, replies[0]["body"])
	assert_in_payload(second, replies[0]["body"])
	assert_not_in_payload(second, replies[25]["body"])


def test_only_the_shown_page_is_marked_read():
	user = factories.user()
	replies = [_notified_reply(user) for _ in range(26)]
	db.execute("UPDATE notifications SET created_datetimez = now() - interval '1 hour' WHERE comment_id = :id", id=replies[0]["id"])
	client = as_user(user)

	with db_diff() as d:
		client.get("/notifications")

	d.assert_exactly(updated={"notifications": {(user["id"], reply["id"]): {"read": True} for reply in replies[1:]}})


def test_api_clients_get_json():
	user = factories.user()
	reply = _notified_reply(user)

	r = as_api(factories.api_token(user)).get("/notifications")

	assert_status(r, 200)
	assert [item["id"] for item in r.json["data"]] == [reply["id"]]


# /notifications/posts

def test_lists_new_post_notifications_newest_first():
	user = factories.user()
	older, newer = _new_post_notification(user), _new_post_notification(user)
	db.execute("UPDATE notifications SET created_datetimez = now() - interval '1 hour' WHERE comment_id = :id", id=older["id"])
	reply = _notified_reply(user)

	r = as_user(user).get("/notifications/posts")

	assert_html(r, 200)
	assert_in_order(r, [newer["text"], older["text"]])
	assert_not_in_payload(r, reply["body"])


def test_showing_new_post_notifications_marks_them_read():
	user = factories.user()
	notice = _new_post_notification(user)
	client = as_user(user)

	with db_diff() as d:
		client.get("/notifications/posts")

	d.assert_exactly(updated={"notifications": {(user["id"], notice["id"]): {"read": True}}})


def test_new_post_notifications_for_api_clients():
	user = factories.user()
	notice = _new_post_notification(user)

	r = as_api(factories.api_token(user)).get("/notifications/posts")

	assert_status(r, 200)
	assert [item["id"] for item in r.json["data"]] == [notice["id"]]


# /notifications/messages

def test_lists_conversations_sent_and_received_newest_first():
	user = factories.user()
	sent = factories.message(user, factories.user())
	received = factories.message(factories.user(), user)
	to_modmail = factories.message(user, seed.MODMAIL_ID)
	others = factories.message(factories.user(), factories.user())

	r = as_user(user).get("/notifications/messages")

	assert_html(r, 200)
	assert_in_order(r, [to_modmail["text"], received["text"], sent["text"]])
	assert_not_in_payload(r, others["text"])


def test_notices_and_comments_are_not_conversations():
	user = factories.user()
	notice = _notice(user)
	reply = _notified_reply(user)

	r = as_user(user).get("/notifications/messages")

	assert_not_in_payload(r, notice["text"])
	assert_not_in_payload(r, reply["body"])


def test_conversations_show_with_their_replies_oldest_first():
	user, other = factories.user(), factories.user()
	message = factories.message(other, user)
	answer = factories.message(user, other, message)
	follow_up = factories.message(other, user, answer, created_utc=answer["created_utc"] + 1)

	assert_in_order(as_user(user).get("/notifications/messages"), [message["text"], answer["text"], follow_up["text"]])


def test_conversations_started_by_blocked_users_are_left_out():
	user, other = factories.user(), factories.user()
	message = factories.message(other, user)
	db.insert("userblocks", user_id=user["id"], target_id=other["id"])

	assert_not_in_payload(as_user(user).get("/notifications/messages"), message["text"])


def test_conversations_started_by_shadowbanned_users_are_left_out_for_users():
	user = factories.user()
	message = factories.message(factories.user(shadowbanned="somemod"), user)

	assert_not_in_payload(as_user(user).get("/notifications/messages"), message["text"])


@pytest.mark.parametrize("level", [2, 3])
def test_conversations_started_by_shadowbanned_users_show_to_admins_from_level_2(level):
	admin = factories.admin(level)
	message = factories.message(factories.user(shadowbanned="somemod"), admin)

	assert_in_payload(as_user(admin).get("/notifications/messages"), message["text"])


def test_shadowbanned_users_dont_see_each_others_conversations():
	user = factories.user(shadowbanned="somemod")
	factories.message(factories.user(shadowbanned="somemod"), user)

	r = as_api(factories.api_token(user)).get("/notifications/messages")

	assert r.json["data"] == []


def test_shadowbanned_users_see_their_own_conversations():
	user = factories.user(shadowbanned="somemod")
	message = factories.message(user, factories.user())

	assert_in_payload(as_user(user).get("/notifications/messages"), message["text"])


def test_conversation_pages_hold_25():
	user = factories.user()
	messages = [factories.message(factories.user(), user) for _ in range(26)]
	client = as_user(user)

	first, second = client.get("/notifications/messages"), client.get("/notifications/messages", params={"page": 2})

	assert_in_payload(first, messages[1]["text"])
	assert_not_in_payload(first, messages[0]["text"])
	assert_in_payload(second, messages[0]["text"])


def test_conversations_for_api_clients():
	user = factories.user()
	message = factories.message(factories.user(), user)

	r = as_api(factories.api_token(user)).get("/notifications/messages")

	assert_status(r, 200)
	assert [item["id"] for item in r.json["data"]] == [message["id"]]
