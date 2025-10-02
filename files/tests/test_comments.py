"""Tests for comment viewing routes."""
from . import util_accounts
from . import util_submissions
from . import util_comments


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
