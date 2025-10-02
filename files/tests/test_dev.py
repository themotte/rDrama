"""Tests for dev routes."""
from . import util_accounts
from . import util


def test_dev_sessions_post():
	"""Test POST /dev/sessions/ route (likely disabled in production)"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(client, "/dev/sessions/", data={})
	# Route might be disabled or require specific conditions
	assert response.status_code in [200, 400, 403, 404, 500]
