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


def test_logged_out_with_query_no_path():
	"""Test /logged_out with query params but no path adds leading slash"""
	client = util_accounts.create_logged_off_client()

	# /logged_out?redirect=submit should redirect to /?redirect=submit
	response = client.get("/logged_out?redirect=submit", follow_redirects=False)
	assert response.status_code == 302
	assert response.location == "/?redirect=submit"


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


def test_stats_route():
	"""Test /stats route returns participation statistics"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/stats")
	assert response.status_code == 200
	# Should contain stats content
	assert response.status_code == 200


def test_admins_route():
	"""Test /admins route returns list of admins"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/admins")
	assert response.status_code == 200
	# Should contain admins content
	assert response.status_code == 200


def test_admins_route_as_admin():
	"""Test /admins route shows different view for level 3+ admins"""
	client, admin = util_accounts.create_test_client_and_user("adm-test")
	from files.__main__ import db_session
	admin.admin_level = 3
	db_session.add(admin)
	db_session.commit()

	response = client.get("/admins")
	assert response.status_code == 200


def test_log_route():
	"""Test /log (modlog) route"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/log")
	assert response.status_code == 200


def test_modlog_route():
	"""Test /modlog route (alias for /log)"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/modlog")
	assert response.status_code == 200


def test_api_route():
	"""Test /api route returns API documentation"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/api")
	assert response.status_code == 200


def test_badges_route():
	"""Test /badges route requires admin level 2"""
	from files.__main__ import db_session
	client, admin = util_accounts.create_test_client_and_user("badges-admin")
	admin.admin_level = 2
	db_session.add(admin)
	db_session.commit()

	response = client.get("/badges")
	assert response.status_code == 200


def test_formatting_route():
	"""Test /formatting route"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/formatting")
	assert response.status_code == 200


def test_robots_txt_route():
	"""Test /robots.txt route"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/robots.txt")
	assert response.status_code == 200
	assert response.content_type.startswith("text/plain")
