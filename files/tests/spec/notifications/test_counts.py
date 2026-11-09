'''
Every page shows a logged-in user how many unread notifications they have (the bell, see `notification_counts`), and the notification pages split it into their tabs: "posts" counts the unread notifications of followed users' new posts, "all" the rest. The bell counts both.

The counts are of what /notifications and /notifications/posts would show (test_pages), unread: read notifications aren't counted, nor notifications of comments that were removed, are held for approval or deleted, nor of comments by users the viewer blocks (except admins' messages), nor of comments by shadowbanned users, except their messages and modmail to admins from level 2.

The bell leads to /notifications/posts when every unread notification is of a new post, else to /notifications.
'''
import pytest

from files.tests.spec.harness import *


def _notified_reply(user, **overrides):
	post = factories.post(user)
	reply = factories.comment(overrides.pop("author", None) or factories.user(), post, parent=factories.comment(user, post), **overrides)
	factories.notification(user, reply)
	return reply


def _notified_message(user, recipient, author):
	'''A message from `author` to `recipient` (`user`, or modmail), of which `user` was notified.'''
	message = factories.message(author, user if recipient == "direct" else seed.MODMAIL_ID)
	factories.notification(user, message)
	return message


def _new_post_notification(user):
	notice = factories.message(db.row("users", id=seed.AUTOJANNY_ID), None, distinguish_level=6)
	factories.notification(user, notice)
	return notice


def _counts(user, path="/notifications/messages"):
	'''The counts as a page shows them; by default the Messages tab, which marks only messages read.'''
	r = as_user(user).get(path)
	assert_html(r, 200)
	return notification_counts(r)


def test_nothing_unread():
	user = factories.user()

	assert _counts(user) == {"bell": 0, "bell_link": "/notifications", "all": 0, "posts": 0}


def test_counts_unread_notifications_by_kind():
	user = factories.user()
	_notified_reply(user)
	_notified_reply(user)
	_new_post_notification(user)

	assert _counts(user) == {"bell": 3, "bell_link": "/notifications", "all": 2, "posts": 1}


def test_other_pages_show_the_bell():
	user = factories.user()
	_notified_reply(user)

	counts = _counts(user, "/")

	assert (counts["bell"], counts["all"], counts["posts"]) == (1, None, None)


def test_only_new_posts_unread_leads_to_their_page():
	user = factories.user()
	_new_post_notification(user)

	assert _counts(user)["bell_link"] == "/notifications/posts"


def test_read_notifications_arent_counted():
	user = factories.user()
	reply = _notified_reply(user)
	db.update("notifications", {"user_id": user["id"], "comment_id": reply["id"]}, read=True)

	assert _counts(user)["bell"] == 0


@pytest.mark.parametrize("state", [{"state_mod": "REMOVED"}, {"state_mod": "FILTERED"}, {"state_user_deleted_utc": "2020-01-01T00:00:00Z"}], ids=["removed", "filtered", "deleted"])
def test_hidden_comments_arent_counted(state):
	user = factories.user()
	_notified_reply(user, **state)

	assert _counts(user)["bell"] == 0


def test_shadowbanned_authors_arent_counted_for_users():
	user = factories.user()
	_notified_reply(user, author=factories.user(shadowbanned="somemod"))

	assert _counts(user)["bell"] == 0


@pytest.mark.parametrize("level", [2, 3])
def test_shadowbanned_authors_arent_counted_for_admins_either(level):
	admin = factories.admin(level)
	_notified_reply(admin, author=factories.user(shadowbanned="somemod"))

	assert _counts(admin)["bell"] == 0


@pytest.mark.parametrize("recipient", ["direct", "modmail"])
@pytest.mark.parametrize("level", [2, 3])
def test_shadowbanned_users_messages_are_counted_for_admins_from_level_2(level, recipient):
	admin = factories.admin(level)
	_notified_message(admin, recipient, factories.user(shadowbanned="somemod"))

	assert _counts(admin, "/")["bell"] == 1


def test_shadowbanned_users_dont_count_each_others_comments():
	user = factories.user(shadowbanned="somemod")
	_notified_reply(user, author=factories.user(shadowbanned="somemod"))

	assert _counts(user)["bell"] == 0


def test_blocked_authors_arent_counted():
	user, author = factories.user(), factories.user()
	_notified_reply(user, author=author)
	db.insert("userblocks", user_id=user["id"], target_id=author["id"])

	assert _counts(user)["bell"] == 0


def test_messages_from_blocked_admins_are_counted():
	user, admin = factories.user(), factories.admin(2)
	factories.notification(user, factories.message(admin, user))
	db.insert("userblocks", user_id=user["id"], target_id=admin["id"])

	assert _counts(user, "/")["bell"] == 1


def test_reading_the_notifications_clears_the_count():
	user = factories.user()
	_notified_reply(user)
	as_user(user).get("/notifications")

	assert _counts(user)["bell"] == 0
