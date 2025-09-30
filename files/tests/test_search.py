from . import util_accounts
from . import util
from . import util_submissions
from . import util_comments


def test_search_posts_basic():
	"""Test basic post search functionality"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post with a unique searchable term
	unique_term = util.generate_text()
	post_title = f"Test Post {unique_term}"
	post_body = "Some body text"

	submission = util_submissions.create_submission_for_client(
		client,
		data={"title": post_title, "body": post_body}
	)

	# Search for the post
	response = client.get(f"/search/posts?q={unique_term}")
	assert response.status_code == 200
	assert unique_term in response.text
	assert post_title in response.text


def test_search_posts_with_author():
	"""Test post search with author filter"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post
	unique_term = util.generate_text()
	post_title = f"Test Post {unique_term}"

	submission = util_submissions.create_submission_for_client(
		client,
		data={"title": post_title, "body": "body"}
	)

	# Search by author
	response = client.get(f"/search/posts?q=author:{user.username}")
	assert response.status_code == 200
	assert post_title in response.text


def test_search_posts_pagination():
	"""Test post search pagination"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post
	unique_term = util.generate_text()
	submission = util_submissions.create_submission_for_client(
		client,
		data={"title": f"Post {unique_term}", "body": "body"}
	)

	# Test page 1
	response = client.get(f"/search/posts?q={unique_term}&page=1")
	assert response.status_code == 200
	assert unique_term in response.text

	# Test page 2 (should work even if empty)
	response = client.get(f"/search/posts?q={unique_term}&page=2")
	assert response.status_code == 200


def test_search_posts_sort_and_time():
	"""Test post search with sort and time filters"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post
	unique_term = util.generate_text()
	submission = util_submissions.create_submission_for_client(
		client,
		data={"title": f"Post {unique_term}", "body": "body"}
	)

	# Test with sort=new and t=all
	response = client.get(f"/search/posts?q={unique_term}&sort=new&t=all")
	assert response.status_code == 200
	assert unique_term in response.text

	# Test with sort=top and t=day
	response = client.get(f"/search/posts?q={unique_term}&sort=top&t=day")
	assert response.status_code == 200


def test_search_comments_basic():
	"""Test basic comment search functionality"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post and comment with unique text
	submission = util_submissions.create_submission_for_client(
		client,
		data={"title": f"Post for comment {util.generate_text()}", "body": "body"}
	)

	unique_comment_text = util.generate_text()
	comment = util_comments.create_comment_for_client(
		client,
		submission.id,
		data={"body": f"Comment with {unique_comment_text}"}
	)

	# Search for the comment
	response = client.get(f"/search/comments?q={unique_comment_text}")
	assert response.status_code == 200
	assert unique_comment_text in response.text


def test_search_comments_with_author():
	"""Test comment search with author filter"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post and comment
	submission = util_submissions.create_submission_for_client(
		client,
		data={"title": f"Post for comment {util.generate_text()}", "body": "body"}
	)

	unique_comment_text = util.generate_text()
	comment = util_comments.create_comment_for_client(
		client,
		submission.id,
		data={"body": f"Comment {unique_comment_text}"}
	)

	# Search by author
	response = client.get(f"/search/comments?q=author:{user.username}")
	assert response.status_code == 200
	assert unique_comment_text in response.text


def test_search_comments_pagination():
	"""Test comment search pagination"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post and comment
	submission = util_submissions.create_submission_for_client(
		client,
		data={"title": f"Post for comment {util.generate_text()}", "body": "body"}
	)

	unique_comment_text = util.generate_text()
	comment = util_comments.create_comment_for_client(
		client,
		submission.id,
		data={"body": f"Comment {unique_comment_text}"}
	)

	# Test page 1
	response = client.get(f"/search/comments?q={unique_comment_text}&page=1")
	assert response.status_code == 200
	assert unique_comment_text in response.text

	# Test page 2 (should work even if empty)
	response = client.get(f"/search/comments?q={unique_comment_text}&page=2")
	assert response.status_code == 200


def test_search_users_basic():
	"""Test basic user search functionality"""
	client, user = util_accounts.create_test_client_and_user()

	# Search for the user we just created
	response = client.get(f"/search/users?q={user.username}")
	assert response.status_code == 200
	assert user.username in response.text


def test_search_users_partial_match():
	"""Test user search with partial username"""
	client, user = util_accounts.create_test_client_and_user()

	# Search with just part of the username
	# Extract a substring from the middle if possible
	username_part = user.username[:5] if len(user.username) >= 5 else user.username[:2]

	response = client.get(f"/search/users?q={username_part}")
	assert response.status_code == 200
	# The user should appear in results since we're doing partial matching
	assert user.username in response.text


def test_search_users_with_at_symbol():
	"""Test user search with @ prefix"""
	client, user = util_accounts.create_test_client_and_user()

	# Search with @ prefix
	response = client.get(f"/search/users?q=@{user.username}")
	assert response.status_code == 200
	assert user.username in response.text


def test_search_users_pagination():
	"""Test user search pagination"""
	client, user = util_accounts.create_test_client_and_user()

	# Test page 1
	response = client.get(f"/search/users?q={user.username}&page=1")
	assert response.status_code == 200
	assert user.username in response.text

	# Test page 2 (should work even if empty)
	response = client.get(f"/search/users?q={user.username}&page=2")
	assert response.status_code == 200


def test_search_posts_logged_out():
	"""Test that logged-out users can search posts"""
	client = util_accounts.create_logged_off_client()

	# Basic search should work without authentication
	response = client.get("/search/posts?q=test")
	assert response.status_code == 200


def test_search_comments_logged_out():
	"""Test that logged-out users can search comments"""
	client = util_accounts.create_logged_off_client()

	# Basic search should work without authentication
	response = client.get("/search/comments?q=test")
	assert response.status_code == 200


def test_search_users_logged_out():
	"""Test that logged-out users can search users"""
	client = util_accounts.create_logged_off_client()

	# Basic search should work without authentication
	response = client.get("/search/users?q=test")
	assert response.status_code == 200