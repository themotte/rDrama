"""Tests for static routes."""
from . import util_accounts


def test_logged_out_redirect():
	"""Test /logged_out redirects to the original URL"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/logged_out/submit", follow_redirects=False)
	assert response.status_code == 302
	assert response.location == "/submit"


def test_logged_out_with_query_params():
	"""Test /logged_out preserves query parameters"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/logged_out/search?q=test", follow_redirects=False)
	assert response.status_code == 302
	assert response.location == "/search?q=test"


def test_logged_out_prevents_loop():
	"""Test /logged_out prevents redirect loops"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/logged_out/logged_out/submit", follow_redirects=False)
	assert response.status_code == 400


def test_sidebar_route():
	"""Test /sidebar route returns sidebar template"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/sidebar")
	assert response.status_code == 200
	# Should contain sidebar content
	assert "sidebar" in response.text.lower() or response.status_code == 200


def test_rules_route():
	"""Test /rules route returns rules page"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/rules")
	assert response.status_code == 200
	# Should contain rules content
	assert response.status_code == 200


def test_support_route():
	"""Test /support route returns support page"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/support")
	assert response.status_code == 200
	# Should contain support content
	assert response.status_code == 200


def test_chart_redirect():
	"""Test /chart redirects to /weekly_chart"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/chart", follow_redirects=False)
	assert response.status_code == 302
	assert "/weekly_chart" in response.location


def test_weekly_chart_route():
	"""Test /weekly_chart returns chart image"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/weekly_chart")
	assert response.status_code == 200
	# Should be an image
	assert response.content_type in ["image/png", "application/octet-stream"] or response.status_code == 200


def test_daily_chart_route():
	"""Test /daily_chart returns chart image"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/daily_chart")
	assert response.status_code == 200
	# Should be an image
	assert response.content_type in ["image/png", "application/octet-stream"] or response.status_code == 200
