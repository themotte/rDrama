"""Tests for comment viewing routes."""
import warnings

from . import util_accounts
from . import util_submissions
from . import util_comments
from . import util
from .conftest import LazyLoadWarning


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


def test_comment_permalink_no_lazy_loads():
	"""Test GET /comment/<cid> doesn't trigger lazy loads (logged in)"""
	client, user = util_accounts.create_test_client_and_user("cpl")

	# Create a post, a top-level comment, and a reply
	post = util_submissions.create_submission_for_client(client)
	parent = util_comments.create_comment_for_client(client, post.id)
	reply = util_comments.create_comment_for_client(client, post.id, data={
		"parent_fullname": f"comment_{parent.id}",
	})

	# View the parent comment permalink and check for lazy loads
	with warnings.catch_warnings(record=True) as w:
		warnings.simplefilter("always")
		response = client.get(f"/comment/{parent.id}")
		assert response.status_code == 200
		lazy_loads = [x for x in w if issubclass(x.category, LazyLoadWarning)]
		assert len(lazy_loads) == 0, f"Lazy loads detected: {[str(x.message) for x in lazy_loads]}"


def test_comment_permalink_logged_out_no_lazy_loads():
	"""Test GET /comment/<cid> doesn't trigger lazy loads (not logged in)"""
	# Create content with a logged-in client
	client, user = util_accounts.create_test_client_and_user("cplo")
	post = util_submissions.create_submission_for_client(client)
	parent = util_comments.create_comment_for_client(client, post.id)
	reply = util_comments.create_comment_for_client(client, post.id, data={
		"parent_fullname": f"comment_{parent.id}",
	})

	# View with a logged-out client
	anon_client = util_accounts.create_logged_off_client()
	with warnings.catch_warnings(record=True) as w:
		warnings.simplefilter("always")
		response = anon_client.get(f"/comment/{parent.id}")
		assert response.status_code == 200
		lazy_loads = [x for x in w if issubclass(x.category, LazyLoadWarning)]
		assert len(lazy_loads) == 0, f"Lazy loads detected: {[str(x.message) for x in lazy_loads]}"
