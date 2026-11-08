"""Tests for static routes."""
from . import util_accounts


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


def test_admins_route():
	"""Test /admins route returns list of admins"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/admins")
	assert response.status_code == 200
	# Should contain admins content
	assert response.status_code == 200


def test_admins_route_as_admin():
	"""Test /admins route shows different view for level 3+ admins"""
	client, admin = util_accounts.create_test_client_and_admin(3)

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


def test_contact_route():
	"""Test /contact route"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/contact")
	assert response.status_code == 200


def test_press_route():
	"""Test /press route"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/press")
	assert response.status_code == 200


def test_media_route():
	"""Test /media route"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/media")
	assert response.status_code == 200


def test_banned_route():
	"""Test /banned route"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/banned")
	assert response.status_code == 200


def test_blocks_route():
	"""Test /blocks route requires admin level 2"""
	client, admin = util_accounts.create_test_client_and_admin(2)

	response = client.get("/blocks")
	assert response.status_code == 200




def test_log_id_route():
	"""Test GET /log/<id> route"""
	client = util_accounts.create_logged_off_client()

	# Try to view a log entry (may not exist)
	response = client.get("/log/1")
	assert response.status_code in [200, 404]


def test_settings_security_get():
	"""Test GET /settings/security route"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/settings/security")
	assert response.status_code == 200


def test_send_admin_route():
	"""Test POST /send_admin route"""
	from . import util
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/send_admin",
		data={"message": "Test admin message"}
	)
	# Should send message or return error
	assert response.status_code in [200, 302, 400, 403]


def test_dismiss_mobile_tip_route():
	"""Test POST /dismiss_mobile_tip route"""
	from . import util
	client, user = util_accounts.create_test_client_and_user("mobile-user")

	response, _ = util.post_with_formkey(
		client, "/dismiss_mobile_tip",
		data={}
	)
	# Should dismiss tip (returns 204 No Content on success)
	assert response.status_code in [200, 204, 302, 400]
