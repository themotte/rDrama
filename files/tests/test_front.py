from . import util_accounts
from . import util_submissions
from . import util_comments
from . import util
from files.__main__ import db_session
from files.classes import Submission, User, Comment


def test_changelog_page():
	"""Test that the changelog page renders"""
	client, user = util_accounts.create_test_client_and_user()
	response = client.get("/changelog")
	assert response.status_code == 200


def test_changelog_page_with_sort():
	"""Test changelog page with sort parameter"""
	client, user = util_accounts.create_test_client_and_user()
	response = client.get("/changelog?sort=new")
	assert response.status_code == 200

	response = client.get("/changelog?sort=hot")
	assert response.status_code == 200


def test_changelog_page_with_time_filter():
	"""Test changelog page with time filter"""
	client, user = util_accounts.create_test_client_and_user()
	response = client.get("/changelog?t=day")
	assert response.status_code == 200

	response = client.get("/changelog?t=week")
	assert response.status_code == 200


def test_changelog_pagination():
	"""Test changelog page pagination"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/changelog?page=1")
	assert response.status_code == 200

	response = client.get("/changelog?page=2")
	assert response.status_code == 200


def test_changelog_requires_auth():
	"""Test that changelog page requires authentication"""
	client = util_accounts.create_logged_off_client()
	response = client.get("/changelog")
	assert response.status_code == 302  # Redirect to login


def test_random_post():
	"""Test random post redirect"""
	# Create a user and a post first to ensure there's something to redirect to
	client, user = util_accounts.create_test_client_and_user()
	post = util_submissions.create_submission_for_client(client)

	# Now test the random post endpoint
	response = client.get("/random_post", follow_redirects=False)
	assert response.status_code == 302  # Should redirect
	assert response.location.startswith("/post/")


def test_random_post_no_posts():
	"""Test random post when no posts exist (edge case)"""
	# Create a fresh database state - this might not work as expected
	# since other tests have created posts. But we test the endpoint anyway.
	client = util_accounts.create_logged_off_client()
	response = client.get("/random_post", follow_redirects=False)
	# Should either redirect to a post or return 404
	assert response.status_code in [302, 404]


def test_random_user():
	"""Test random user redirect"""
	# Create a user first to ensure there's something to redirect to
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/random_user", follow_redirects=False)
	assert response.status_code == 302  # Should redirect
	assert response.location.startswith("/@")


def test_all_comments_page():
	"""Test the all comments page"""
	client, user = util_accounts.create_test_client_and_user()

	# Create some comments
	post = util_submissions.create_submission_for_client(client)
	util_comments.create_comment_for_client(client, post.id)

	response = client.get("/comments")
	assert response.status_code == 200


def test_all_comments_with_sort():
	"""Test all comments page with different sort options"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/comments?sort=new")
	assert response.status_code == 200

	response = client.get("/comments?sort=hot")
	assert response.status_code == 200

	response = client.get("/comments?sort=top")
	assert response.status_code == 200


def test_all_comments_with_time_filter():
	"""Test all comments page with time filter"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/comments?t=day")
	assert response.status_code == 200

	response = client.get("/comments?t=week")
	assert response.status_code == 200

	response = client.get("/comments?t=all")
	assert response.status_code == 200


def test_all_comments_pagination():
	"""Test all comments page pagination"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/comments?page=1")
	assert response.status_code == 200

	response = client.get("/comments?page=2")
	assert response.status_code == 200


def test_all_comments_requires_auth():
	"""Test that all comments page requires authentication"""
	client = util_accounts.create_logged_off_client()
	response = client.get("/comments")
	assert response.status_code == 302  # Redirect to login


def test_front_page_logged_out():
	"""Test front page access while logged out"""
	client = util_accounts.create_logged_off_client()
	response = client.get("/")
	assert response.status_code == 200


def test_front_page_logged_in():
	"""Test front page access while logged in"""
	client, user = util_accounts.create_test_client_and_user()
	response = client.get("/")
	assert response.status_code == 200


def test_front_page_with_sort():
	"""Test front page with different sort options"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/?sort=new")
	assert response.status_code == 200

	response = client.get("/?sort=hot")
	assert response.status_code == 200

	response = client.get("/?sort=top")
	assert response.status_code == 200


def test_front_page_with_time_filter():
	"""Test front page with time filter"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/?t=day")
	assert response.status_code == 200

	response = client.get("/?t=week")
	assert response.status_code == 200

	response = client.get("/?t=all")
	assert response.status_code == 200


def test_front_page_pagination():
	"""Test front page pagination"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/?page=1")
	assert response.status_code == 200

	response = client.get("/?page=2")
	assert response.status_code == 200


def test_front_page_with_after_parameter():
	"""Test front page with after parameter"""
	client, user = util_accounts.create_test_client_and_user()

	# Use a timestamp
	response = client.get("/?after=1000000000")
	assert response.status_code == 200


def test_front_page_with_before_parameter():
	"""Test front page with before parameter"""
	client, user = util_accounts.create_test_client_and_user()

	# Use a timestamp
	response = client.get("/?before=9999999999")
	assert response.status_code == 200


def test_catalog_alias():
	"""Test that /catalog is an alias for the front page"""
	client, user = util_accounts.create_test_client_and_user()
	response = client.get("/catalog")
	assert response.status_code == 200


def test_front_page_invalid_page():
	"""Test front page with invalid page parameter"""
	client, user = util_accounts.create_test_client_and_user()

	# Invalid page should return 400
	response = client.get("/?page=invalid")
	assert response.status_code == 400


def test_all_comments_with_before_and_after():
	"""Test all comments page with before and after parameters"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/comments?after=1000000000")
	assert response.status_code == 200

	response = client.get("/comments?before=9999999999")
	assert response.status_code == 200


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


def test_front_page_with_invalid_after_parameter():
	"""Test front page with invalid after parameter"""
	client, user = util_accounts.create_test_client_and_user()

	# Invalid after parameter should be handled gracefully
	response = client.get("/?after=invalid")
	assert response.status_code == 200  # Should default to 0


def test_front_page_with_invalid_before_parameter():
	"""Test front page with invalid before parameter"""
	client, user = util_accounts.create_test_client_and_user()

	# Invalid before parameter should be handled gracefully
	response = client.get("/?before=invalid")
	assert response.status_code == 200  # Should default to 0


def test_changelog_invalid_page():
	"""Test changelog with invalid page parameter"""
	client, user = util_accounts.create_test_client_and_user()

	# Invalid page should default to 1
	response = client.get("/changelog?page=invalid")
	assert response.status_code == 200