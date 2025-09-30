from . import util_accounts
from . import util_submissions
from . import util_comments
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


def test_notifications_pagination():
	"""Test notifications page pagination"""
	client, user = util_accounts.create_test_client_and_user(name="notif-page")

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
	client, user = util_accounts.create_test_client_and_user(name="notif-posts")

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
	client, user = util_accounts.create_test_client_and_user(name="notif-modmail")

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
	client, user = util_accounts.create_test_client_and_user(name="msg-page")

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