from . import util_accounts
from . import util


def test_settings_redirect_to_profile():
	"""Test /settings redirects to /settings/profile"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/settings")
	assert response.status_code == 302
	assert "/settings/profile" in response.location


def test_settings_profile_get():
	"""Test accessing the profile settings page"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/settings/profile")
	assert response.status_code == 200
	assert "settings" in response.text.lower()


def test_settings_profile_requires_auth():
	"""Test profile settings requires authentication"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/settings/profile")
	assert response.status_code == 302
	assert "/login" in response.location


def test_settings_blocks_get():
	"""Test accessing the blocks settings page"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/settings/blocks")
	assert response.status_code == 200
	assert "block" in response.text.lower()


def test_settings_css_get():
	"""Test accessing the CSS settings page"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/settings/css")
	assert response.status_code == 200


def test_settings_css_post():
	"""Test updating CSS settings"""
	client, user = util_accounts.create_test_client_and_user()

	# Set some valid CSS
	css = "body { color: red; }"
	response, _ = util.post_with_formkey(
		client, "/settings/css",
		data={"css": css}
	)
	assert response.status_code == 200

	# Verify the CSS was saved
	from files.__main__ import db_session
	from files.classes import User
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.css == css


def test_settings_css_post_empty():
	"""Test posting empty CSS clears it"""
	client, user = util_accounts.create_test_client_and_user()

	# Set empty CSS
	css = ""
	response, _ = util.post_with_formkey(
		client, "/settings/css",
		data={"css": css}
	)
	assert response.status_code == 200

	# Verify the CSS was saved as empty
	from files.__main__ import db_session
	from files.classes import User
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.css == ""


def test_settings_profilecss_get():
	"""Test accessing the profile CSS settings page"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/settings/profilecss")
	assert response.status_code == 200


def test_settings_profilecss_post():
	"""Test updating profile CSS settings"""
	client, user = util_accounts.create_test_client_and_user()

	# Set some valid CSS
	css = ".profile { background: blue; }"
	response, _ = util.post_with_formkey(
		client, "/settings/profilecss",
		data={"profilecss": css}
	)
	assert response.status_code == 200

	# Verify the CSS was saved
	from files.__main__ import db_session
	from files.classes import User
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.profilecss == css


def test_settings_profilecss_post_empty():
	"""Test posting empty profile CSS clears it"""
	client, user = util_accounts.create_test_client_and_user()

	# Set empty CSS
	css = ""
	response, _ = util.post_with_formkey(
		client, "/settings/profilecss",
		data={"profilecss": css}
	)
	assert response.status_code == 200

	# Verify the CSS was saved as empty
	from files.__main__ import db_session
	from files.classes import User
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.profilecss == ""


def test_settings_apps_get():
	"""Test accessing the apps settings page"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/settings/apps")
	assert response.status_code == 200


def test_settings_content_get():
	"""Test accessing the content/filters settings page"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/settings/content")
	assert response.status_code == 200
	assert "filter" in response.text.lower()


def test_settings_block_endpoint_exists():
	"""Test that the block endpoint exists and requires auth"""
	client = util_accounts.create_logged_off_client()

	# Should require auth
	response = client.post("/settings/block")
	assert response.status_code == 302  # Redirect to login


def test_settings_block_self():
	"""Test that you cannot block yourself"""
	client, user = util_accounts.create_test_client_and_user()

	# Try to block yourself
	response, _ = util.post_with_formkey(
		client, "/settings/block",
		data={"username": user.username}
	)
	assert response.status_code == 409


def test_settings_block_nonexistent_user():
	"""Test blocking a nonexistent user returns 404"""
	client, user = util_accounts.create_test_client_and_user()

	# Try to block nonexistent user
	response, _ = util.post_with_formkey(
		client, "/settings/block",
		data={"username": "nonexistent_user_12345"}
	)
	assert response.status_code == 404


def test_settings_unblock_endpoint_exists():
	"""Test that the unblock endpoint exists and requires auth"""
	client = util_accounts.create_logged_off_client()

	# Should require auth
	response = client.post("/settings/unblock")
	assert response.status_code == 302  # Redirect to login


def test_settings_unblock_not_blocked():
	"""Test unblocking a user you haven't blocked returns 409"""
	client1, user1 = util_accounts.create_test_client_and_user()
	client2, user2 = util_accounts.create_test_client_and_user()

	# Try to unblock without having blocked
	response, _ = util.post_with_formkey(
		client1, "/settings/unblock",
		data={"username": user2.username}
	)
	assert response.status_code == 409


def test_settings_all_pages_require_auth():
	"""Test that all settings pages require authentication"""
	client = util_accounts.create_logged_off_client()

	pages = [
		"/settings",
		"/settings/profile",
		"/settings/blocks",
		"/settings/css",
		"/settings/profilecss",
		"/settings/apps",
		"/settings/content",
	]

	for page in pages:
		response = client.get(page)
		assert response.status_code == 302, f"{page} should redirect when not authenticated"
		assert "/login" in response.location, f"{page} should redirect to login"