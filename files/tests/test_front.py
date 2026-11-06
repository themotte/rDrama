from . import util_accounts
from . import util_submissions
from . import util_comments
from . import util
from files.__main__ import db_session
from files.classes import Submission, User, Comment


def test_notifications_clear():
	"""Test clearing notifications"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post and comment to generate a notification
	post = util_submissions.create_submission_for_client(client)
	util_comments.create_comment_for_client(client, post.id)

	# Clear notifications - use formkey for POST request
	response, _ = util.post_with_formkey(client, "/clear", data={})
	assert response.status_code == 200


def test_unread_notifications():
	"""Test getting unread notifications"""
	client, user = util_accounts.create_test_client_and_user()

	# Get unread notifications
	response = client.get("/unread")
	assert response.status_code == 200
	assert "data" in response.json


def test_notifications_page():
	"""Test notifications page"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/notifications")
	assert response.status_code == 200


def test_notifications_page_with_pagination():
	"""Test notifications page with pagination"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/notifications?page=2")
	assert response.status_code == 200


def test_notifications_posts_page():
	"""Test notifications/posts page"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/notifications/posts")
	assert response.status_code == 200


def test_notifications_posts_with_pagination():
	"""Test notifications/posts page with pagination to hit read status tracking"""
	client, user = util_accounts.create_test_client_and_user()

	# Test pagination
	response = client.get("/notifications/posts?page=1")
	assert response.status_code == 200

	response = client.get("/notifications/posts?page=2")
	assert response.status_code == 200


def test_notifications_messages():
	"""Test notifications/messages page"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/notifications/messages")
	assert response.status_code == 200


def test_notifications_modmail():
	"""Test notifications/modmail page"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/notifications/modmail")
	# May require moderator permissions
	assert response.status_code in [200, 403]
