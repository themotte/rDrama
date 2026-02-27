import warnings

from . import util_accounts
from . import util_submissions
from . import util_comments
from .conftest import LazyLoadWarning
from files.__main__ import db_session
from files.classes import Notification, Comment, User


def test_clear_notifications():
	"""Test clearing all notifications"""
	# Create two users
	client1, user1 = util_accounts.create_test_client_and_user(name="notif-user1")
	client2, user2 = util_accounts.create_test_client_and_user(name="notif-user2")

	# User1 creates a post and comment
	post = util_submissions.create_submission_for_client(client1)
	comment = util_comments.create_comment_for_client(client1, post.id)

	# User2 replies to user1's comment (this creates a notification)
	util_comments.create_comment_for_client(client2, post.id, data={
		'parent_fullname': f'comment_{comment.id}',
		'parent_level': 2,
	})

	# Verify user1 has unread notifications
	db = db_session()
	unread_count = db.query(Notification).filter(
		Notification.user_id == user1.id,
		Notification.read == False
	).count()
	assert unread_count > 0

	# User1 clears notifications
	response, _ = util_accounts.util.post_with_formkey(client1, "/clear", data={})
	assert response.status_code == 200
	assert "cleared" in response.text.lower()

	# Verify all notifications are marked as read
	db.expire_all()
	unread_count = db.query(Notification).filter(
		Notification.user_id == user1.id,
		Notification.read == False
	).count()
	assert unread_count == 0


def test_clear_notifications_requires_auth():
	"""Test that clearing notifications requires authentication"""
	client = util_accounts.create_logged_off_client()
	response = client.post("/clear")
	assert response.status_code == 302  # Redirect to login


def test_unread_notifications():
	"""Test getting unread notifications via API"""
	# Create two users
	client1, user1 = util_accounts.create_test_client_and_user(name="unread-user1")
	client2, user2 = util_accounts.create_test_client_and_user(name="unread-user2")

	# User1 creates a post and comment
	post = util_submissions.create_submission_for_client(client1)
	comment = util_comments.create_comment_for_client(client1, post.id)

	# User2 replies to user1's comment
	reply = util_comments.create_comment_for_client(client2, post.id, data={
		'parent_fullname': f'comment_{comment.id}',
		'parent_level': 2,
	})

	# User1 gets unread notifications
	response = client1.get("/unread")
	assert response.status_code == 200

	import json
	data = json.loads(response.text)
	assert "data" in data
	assert len(data["data"]) > 0

	# Verify notifications are now marked as read
	db = db_session()
	db.expire_all()
	unread_count = db.query(Notification).filter(
		Notification.user_id == user1.id,
		Notification.read == False
	).count()
	assert unread_count == 0


def test_unread_notifications_requires_auth():
	"""Test that unread endpoint requires authentication"""
	client = util_accounts.create_logged_off_client()
	response = client.get("/unread")
	assert response.status_code == 302  # Redirect to login


def test_notifications_main_page():
	"""Test the main notifications page"""
	# Create two users
	client1, user1 = util_accounts.create_test_client_and_user(name="notif-main1")
	client2, user2 = util_accounts.create_test_client_and_user(name="notif-main2")

	# User1 creates a post and comment
	post = util_submissions.create_submission_for_client(client1)
	comment = util_comments.create_comment_for_client(client1, post.id)

	# User2 replies to user1's comment
	util_comments.create_comment_for_client(client2, post.id, data={
		'parent_fullname': f'comment_{comment.id}',
		'parent_level': 2,
	})

	# User1 views notifications page
	response = client1.get("/notifications")
	assert response.status_code == 200
	assert "notification" in response.text.lower()


def test_notifications_no_lazy_loads():
	"""Test GET /notifications doesn't trigger lazy loads.

	Creates a comment tree so that the notification comment has children,
	which would trigger lazy loads in replies() if not properly handled.
	"""
	client1, user1 = util_accounts.create_test_client_and_user(name="notif-nll1")
	client2, user2 = util_accounts.create_test_client_and_user(name="notif-nll2")
	client3, user3 = util_accounts.create_test_client_and_user(name="notif-nll3")

	# User1 creates a post and comment
	post = util_submissions.create_submission_for_client(client1)
	comment = util_comments.create_comment_for_client(client1, post.id)

	# User2 replies to user1's comment (creates a notification for user1)
	reply = util_comments.create_comment_for_client(client2, post.id, data={
		'parent_fullname': f'comment_{comment.id}',
		'parent_level': 2,
	})

	# User3 replies to user2's reply (so the notification comment has children)
	util_comments.create_comment_for_client(client3, post.id, data={
		'parent_fullname': f'comment_{reply.id}',
		'parent_level': 3,
	})

	# User1 views notifications page — capture lazy load warnings
	with warnings.catch_warnings(record=True) as w:
		warnings.simplefilter("always")
		response = client1.get("/notifications")
		assert response.status_code == 200
		lazy_loads = [x for x in w if issubclass(x.category, LazyLoadWarning)]
		assert len(lazy_loads) == 0, \
			f"Lazy loads detected: {[str(x.message) for x in lazy_loads]}"


def test_notifications_pagination():
	"""Test notifications page pagination"""
	client, user = util_accounts.create_test_client_and_user()

	# Get page 1
	response = client.get("/notifications?page=1")
	assert response.status_code == 200

	# Get page 2
	response = client.get("/notifications?page=2")
	assert response.status_code == 200


def test_notifications_requires_auth():
	"""Test that notifications page requires authentication"""
	client = util_accounts.create_logged_off_client()
	response = client.get("/notifications")
	assert response.status_code == 302  # Redirect to login


def test_notifications_posts_page():
	"""Test the post notifications page (AUTOJANNY messages)"""
	client, user = util_accounts.create_test_client_and_user()

	# This page shows notifications from AUTOJANNY only
	response = client.get("/notifications/posts")
	assert response.status_code == 200


def test_notifications_posts_requires_auth():
	"""Test that post notifications page requires authentication"""
	client = util_accounts.create_logged_off_client()
	response = client.get("/notifications/posts")
	assert response.status_code == 302  # Redirect to login


def test_notifications_modmail_requires_admin():
	"""Test that modmail notifications require admin level 2+"""
	client, user = util_accounts.create_test_client_and_user()

	# Regular user should not have access
	response = client.get("/notifications/modmail")
	assert response.status_code == 403


def test_notifications_messages_page():
	"""Test the messages page for direct messages"""
	# Create two users
	client1, user1 = util_accounts.create_test_client_and_user(name="msg-user1")
	client2, user2 = util_accounts.create_test_client_and_user(name="msg-user2")

	# User1 views their messages page
	response = client1.get("/notifications/messages")
	assert response.status_code == 200


def test_notifications_messages_pagination():
	"""Test messages page pagination"""
	client, user = util_accounts.create_test_client_and_user()

	# Get page 1
	response = client.get("/notifications/messages?page=1")
	assert response.status_code == 200

	# Get page 2
	response = client.get("/notifications/messages?page=2")
	assert response.status_code == 200


def test_notifications_messages_requires_auth():
	"""Test that messages page requires authentication"""
	client = util_accounts.create_logged_off_client()
	response = client.get("/notifications/messages")
	assert response.status_code == 302  # Redirect to login


# ---- Blocked user notification filtering tests (#640) ----

import json
from . import util


def test_blocked_user_not_in_unread():
	"""Notifications from blocked users should not appear in /unread"""
	client1, user1 = util_accounts.create_test_client_and_user(name="blk-unrd1")
	client2, user2 = util_accounts.create_test_client_and_user(name="blk-unrd2")

	# User1 creates a post and comment
	post = util_submissions.create_submission_for_client(client1)
	comment = util_comments.create_comment_for_client(client1, post.id)

	# User1 blocks User2
	response, _ = util.post_with_formkey(
		client1, "/settings/block",
		data={"username": user2.username}
	)
	assert response.status_code == 200

	# User2 replies to User1's comment (creates a notification)
	util_comments.create_comment_for_client(client2, post.id, data={
		'parent_fullname': f'comment_{comment.id}',
		'parent_level': 2,
	})

	# Verify a notification was created in the database
	db = db_session()
	db.expire_all()
	notif_count = db.query(Notification).filter(
		Notification.user_id == user1.id,
		Notification.read == False,
	).count()
	assert notif_count > 0, "Notification should exist in DB even from blocked user"

	# User1 checks /unread -- blocked user's notification should be filtered
	response = client1.get("/unread")
	assert response.status_code == 200
	data = json.loads(response.text)
	assert "data" in data

	# None of the returned notifications should be from the blocked user
	for notif in data["data"]:
		assert notif.get("author_id") != user2.id, \
			"Notification from blocked user should not appear in /unread"


def test_unblocked_user_appears_in_unread():
	"""Notifications from non-blocked users should still appear in /unread"""
	client1, user1 = util_accounts.create_test_client_and_user(name="nblk-unrd1")
	client2, user2 = util_accounts.create_test_client_and_user(name="nblk-unrd2")

	# User1 creates a post and comment (no blocking)
	post = util_submissions.create_submission_for_client(client1)
	comment = util_comments.create_comment_for_client(client1, post.id)

	# User2 replies to User1's comment
	util_comments.create_comment_for_client(client2, post.id, data={
		'parent_fullname': f'comment_{comment.id}',
		'parent_level': 2,
	})

	# User1 checks /unread -- should see the notification
	response = client1.get("/unread")
	assert response.status_code == 200
	data = json.loads(response.text)
	assert "data" in data
	assert len(data["data"]) > 0, \
		"Notification from non-blocked user should appear in /unread"


def test_blocked_user_not_in_notifications_page():
	"""Notifications from blocked users should not appear on /notifications page"""
	client1, user1 = util_accounts.create_test_client_and_user(name="blk-noti1")
	client2, user2 = util_accounts.create_test_client_and_user(name="blk-noti2")

	# User1 creates a post and comment
	post = util_submissions.create_submission_for_client(client1)
	comment = util_comments.create_comment_for_client(client1, post.id)

	# User1 blocks User2
	response, _ = util.post_with_formkey(
		client1, "/settings/block",
		data={"username": user2.username}
	)
	assert response.status_code == 200

	# User2 replies to User1's comment
	util_comments.create_comment_for_client(client2, post.id, data={
		'parent_fullname': f'comment_{comment.id}',
		'parent_level': 2,
	})

	# User1 checks /notifications page (HTML)
	response = client1.get("/notifications")
	assert response.status_code == 200

	# The blocked user's username should not appear as a comment author
	# in the notifications page. Use a targeted check: the username
	# appears in a user profile link like /@username in notifications.
	assert f"/@{user2.username}" not in response.text, \
		"Blocked user's profile link should not appear in /notifications"


def test_blocking_after_notification_hides_it():
	"""Blocking a user after receiving a notification should hide that notification"""
	client1, user1 = util_accounts.create_test_client_and_user(name="blkaft1")
	client2, user2 = util_accounts.create_test_client_and_user(name="blkaft2")

	# User1 creates a post and comment
	post = util_submissions.create_submission_for_client(client1)
	comment = util_comments.create_comment_for_client(client1, post.id)

	# User2 replies to User1's comment (creates notification BEFORE block)
	util_comments.create_comment_for_client(client2, post.id, data={
		'parent_fullname': f'comment_{comment.id}',
		'parent_level': 2,
	})

	# Verify User1 can see the notification on /notifications page before blocking
	response = client1.get("/notifications")
	assert response.status_code == 200
	assert f"/@{user2.username}" in response.text, \
		"Should see notification from user2 before blocking"

	# Now User1 blocks User2
	response, _ = util.post_with_formkey(
		client1, "/settings/block",
		data={"username": user2.username}
	)
	assert response.status_code == 200

	# User1 checks /notifications page -- notification should be hidden now
	response = client1.get("/notifications")
	assert response.status_code == 200
	assert f"/@{user2.username}" not in response.text, \
		"Notification should be hidden after blocking the author"


def test_blocked_user_not_in_messages():
	"""Messages from blocked users should not appear in /notifications/messages"""
	client1, user1 = util_accounts.create_test_client_and_user(name="blk-msg1")
	client2, user2 = util_accounts.create_test_client_and_user(name="blk-msg2")

	# User2 sends a direct message to User1 (before being blocked)
	response, _ = util.post_with_formkey(
		client2, f"/@{user1.username}/message",
		data={"message": "Hello from a soon-to-be-blocked user"}
	)
	assert response.status_code == 200

	# Verify message exists by checking User1's messages page before blocking
	response = client1.get("/notifications/messages")
	assert response.status_code == 200
	assert f"/@{user2.username}" in response.text, \
		"Message sender's profile link should appear before blocking"

	# User1 blocks User2
	response, _ = util.post_with_formkey(
		client1, "/settings/block",
		data={"username": user2.username}
	)
	assert response.status_code == 200

	# User1 checks /notifications/messages -- blocked user's message should be filtered
	response = client1.get("/notifications/messages")
	assert response.status_code == 200
	assert f"/@{user2.username}" not in response.text, \
		"Blocked user's profile link should not appear in /notifications/messages"
