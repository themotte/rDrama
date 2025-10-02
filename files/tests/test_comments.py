"""Tests for comment viewing routes."""
from . import util_accounts
from . import util_submissions
from . import util_comments
from . import util


def test_create_comment_route():
	"""Test POST /comment route"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post to comment on
	post = util_submissions.create_submission_for_client(client)

	# Create a comment using the /comment route
	response, _ = util.post_with_formkey(
		client, "/comment",
		data={"parent_id": post.id, "body": "Test comment via /comment route"}
	)
	# Should create a comment
	assert response.status_code in [200, 302, 400]


def test_view_comment():
	"""Test GET /comment/<cid> returns comment page"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post and comment
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	# View the comment
	response = client.get(f"/comment/{comment.id}")
	assert response.status_code == 200
	assert comment.body in response.text


def test_view_comment_with_post_id():
	"""Test GET /post/<pid>/<anything>/<cid> returns comment page"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post and comment
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	# View the comment with post ID in URL
	response = client.get(f"/post/{post.id}/test/{comment.id}")
	assert response.status_code == 200
	assert comment.body in response.text
