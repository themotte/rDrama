'''
GET /unread gives a logged-in user's unread notifications as {"data": [...]}, newest first, and marks them read. It holds what /notifications would show (test_pages), unread: not notifications of followed users' new posts, not comments that were removed, are held for approval or deleted, not comments by users the viewer blocks (except messages from admins from level 2), and not, except to admins from level 2, comments by shadowbanned users.

POST /clear marks every one of the user's notifications read, whether or not any page would show it, and replies {"message": ...}.

Both are for logged-in users and API clients; others are refused.
'''
import pytest

from files.tests.spec.harness import *


def _notified_reply(user, **overrides):
	post = factories.post(user)
	reply = factories.comment(overrides.pop("author", None) or factories.user(), post, parent=factories.comment(user, post), **overrides)
	factories.notification(user, reply)
	return reply


def _new_post_notification(user):
	notice = factories.message(db.row("users", id=seed.AUTOJANNY_ID), None, distinguish_level=6)
	factories.notification(user, notice)
	return notice


def _unread_ids(client):
	r = client.get("/unread")
	assert_status(r, 200)
	return [item["id"] for item in r.json["data"]]


@pytest.mark.parametrize("method, path", [("get", "/unread"), ("post", "/clear")])
def test_logged_out_visitors_are_refused(method, path):
	assert_api_unauthorized(getattr(anon(), method)(path, headers=XHR))


def test_lists_unread_newest_first_and_marks_them_read():
	user = factories.user()
	older, newer = _notified_reply(user), _notified_reply(user)
	db.execute("UPDATE notifications SET created_datetimez = now() - interval '1 hour' WHERE comment_id = :id", id=older["id"])
	read = _notified_reply(user)
	db.update("notifications", {"user_id": user["id"], "comment_id": read["id"]}, read=True)
	client = as_api(factories.api_token(user))

	with db_diff() as d:
		ids = _unread_ids(client)

	assert ids == [newer["id"], older["id"]]
	d.assert_exactly(updated={"notifications": {(user["id"], c["id"]): {"read": True} for c in (older, newer)}})


def test_through_the_browser():
	user = factories.user()
	reply = _notified_reply(user)

	assert _unread_ids(as_user(user)) == [reply["id"]]


def test_lists_messages():
	user = factories.user()
	message = factories.message(factories.user(), user)
	factories.notification(user, message)

	assert _unread_ids(as_user(user)) == [message["id"]]


def test_new_post_notifications_are_left_out_and_stay_unread():
	user = factories.user()
	_new_post_notification(user)
	client = as_user(user)

	with db_diff() as d:
		ids = _unread_ids(client)

	assert ids == []
	d.assert_exactly()


@pytest.mark.parametrize("state", [{"state_mod": "REMOVED"}, {"state_mod": "FILTERED"}, {"state_user_deleted_utc": "2020-01-01T00:00:00Z"}], ids=["removed", "filtered", "deleted"])
def test_hidden_comments_are_left_out(state):
	user = factories.user()
	_notified_reply(user, **state)

	assert _unread_ids(as_user(user)) == []


def test_blocked_authors_are_left_out():
	user, author = factories.user(), factories.user()
	_notified_reply(user, author=author)
	db.insert("userblocks", user_id=user["id"], target_id=author["id"])

	assert _unread_ids(as_user(user)) == []


def test_shadowbanned_authors_are_left_out_for_users():
	user = factories.user()
	_notified_reply(user, author=factories.user(shadowbanned="somemod"))

	assert _unread_ids(as_user(user)) == []


@pytest.mark.parametrize("level", [2, 3])
def test_shadowbanned_authors_are_listed_for_admins_from_level_2(level):
	admin = factories.admin(level)
	reply = _notified_reply(admin, author=factories.user(shadowbanned="somemod"))

	assert _unread_ids(as_user(admin)) == [reply["id"]]


def test_messages_from_blocked_admins_are_listed():
	user, admin = factories.user(), factories.admin(2)
	message = factories.message(admin, user)
	factories.notification(user, message)
	db.insert("userblocks", user_id=user["id"], target_id=admin["id"])

	assert _unread_ids(as_user(user)) == [message["id"]]


@pytest.mark.parametrize("client", ["browser", "api"])
def test_clear_marks_everything_read(client):
	user = factories.user()
	shown = _notified_reply(user)
	notice = _new_post_notification(user)
	hidden = _notified_reply(user, state_mod="REMOVED")
	c = as_user(user) if client == "browser" else as_api(factories.api_token(user))

	with db_diff() as d:
		r = c.post("/clear")

	assert_json_message(r)
	d.assert_exactly(updated={"notifications": {(user["id"], x["id"]): {"read": True} for x in (shown, notice, hidden)}})
