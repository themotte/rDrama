import warnings

from . import util_accounts
from . import util_submissions
from . import util_comments
from . import util
from .conftest import LazyLoadWarning
from files.__main__ import db_session
from files.classes import Notification, Comment, User
from files.helpers.config.const import MODMAIL_ID


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


def test_reply_to_own_pm_notifications_no_crash():
	"""Test that replying to your own PM doesn't crash notifications (#683).

	When a user sends a PM and then replies to their own message,
	the notifications page should still load without error.
	"""
	client1, user1 = util_accounts.create_test_client_and_user(name="pm-self1")
	client2, user2 = util_accounts.create_test_client_and_user(name="pm-self2")

	# User1 sends a PM to user2
	response, _ = util.post_with_formkey(
		client1, f"/@{user2.username}/message",
		data={"message": util.generate_text()}
	)
	assert response.status_code == 200

	# Find the PM in the database
	db = db_session()
	pm = db.query(Comment).filter_by(
		author_id=user1.id,
		sentto=user2.id,
		parent_submission=None,
		level=1,
	).first()
	assert pm is not None

	# User1 replies to their own PM
	reply_response, _ = util.post_with_formkey(
		client1, "/reply",
		data={"parent_id": pm.id, "body": util.generate_text()}
	)
	assert reply_response.status_code == 200

	# Verify user2's notifications page loads without crashing
	response = client2.get("/notifications")
	assert response.status_code == 200

	# Verify user2's messages page loads without crashing
	response = client2.get("/notifications/messages")
	assert response.status_code == 200

	# Verify user1's notifications page also loads without crashing
	response = client1.get("/notifications")
	assert response.status_code == 200


def test_reply_to_own_modmail_sets_sentto_correctly():
	"""Test that replying to your own modmail keeps sentto=MODMAIL_ID (#683).

	When a user sends modmail and then replies to their own modmail message,
	the reply should have sentto=MODMAIL_ID so it stays in the modmail thread
	and doesn't end up with sentto=None (which caused the original crash).
	"""
	client1, user1 = util_accounts.create_test_client_and_user(name="mm-self")

	# User1 sends modmail via /send_admin
	response, _ = util.post_with_formkey(
		client1, "/send_admin",
		data={"message": util.generate_text()}
	)
	assert response.status_code == 200

	# Find the modmail in the database
	db = db_session()
	modmail = db.query(Comment).filter_by(
		author_id=user1.id,
		sentto=MODMAIL_ID,
		parent_submission=None,
		level=1,
	).first()
	assert modmail is not None

	# User1 replies to their own modmail
	reply_response, _ = util.post_with_formkey(
		client1, "/reply",
		data={"parent_id": modmail.id, "body": util.generate_text()}
	)
	assert reply_response.status_code == 200

	# Find the reply in the database
	db.expire_all()
	reply = db.query(Comment).filter_by(
		author_id=user1.id,
		parent_comment_id=modmail.id,
	).first()
	assert reply is not None
	# The reply should have sentto=MODMAIL_ID, not None
	assert reply.sentto == MODMAIL_ID, \
		f"Reply sentto should be MODMAIL_ID ({MODMAIL_ID}), got {reply.sentto}"

	# Verify notifications pages load without crashing
	response = client1.get("/notifications")
	assert response.status_code == 200

	response = client1.get("/notifications/messages")
	assert response.status_code == 200
