"""Tests for awards routes (currently disabled)."""
from . import util_accounts
from . import util
from . import util_submissions
from . import util_comments


def test_shop_route_disabled():
	"""Test /shop route is disabled (returns 404)"""
	client, user = util_accounts.create_test_client_and_admin(2)

	response = client.get("/shop")
	assert response.status_code == 404


def test_settings_shop_route_disabled():
	"""Test /settings/shop route is disabled (returns 404)"""
	client, user = util_accounts.create_test_client_and_admin(2)

	response = client.get("/settings/shop")
	assert response.status_code == 404


def test_buy_award_route_disabled():
	"""Test POST /buy/<award> route is disabled (returns 404)"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/buy/test-award",
		data={}
	)
	assert response.status_code == 404


def test_award_post_route_disabled():
	"""Test POST /award_post/<pid> route is disabled (returns 404)"""
	client, user = util_accounts.create_test_client_and_user()
	post = util_submissions.create_submission_for_client(client)

	response, _ = util.post_with_formkey(
		client, f"/award_post/{post.id}",
		data={}
	)
	assert response.status_code == 404


def test_award_comment_route_disabled():
	"""Test POST /award_comment/<cid> route is disabled (returns 404)"""
	client, user = util_accounts.create_test_client_and_user()
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	response, _ = util.post_with_formkey(
		client, f"/award_comment/{comment.id}",
		data={}
	)
	assert response.status_code == 404


def test_admin_awards_get_route_disabled():
	"""Test GET /admin/awards route is disabled (returns 404)"""
	client, user = util_accounts.create_test_client_and_admin(2)

	response = client.get("/admin/awards")
	assert response.status_code == 404


def test_admin_awards_post_route_disabled():
	"""Test POST /admin/awards route is disabled (returns 404)"""
	client, user = util_accounts.create_test_client_and_admin(2)

	response, _ = util.post_with_formkey(
		client, "/admin/awards",
		data={}
	)
	assert response.status_code == 404
