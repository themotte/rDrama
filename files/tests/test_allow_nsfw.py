import time
from . import util_accounts


def test_allow_nsfw_no_redirect():
	"""Test /allow_nsfw without redirect parameter - should redirect to /"""
	client = util_accounts.create_logged_off_client()

	response = client.post("/allow_nsfw")

	assert response.status_code == 302
	assert response.location == "/"

	# Verify session was set
	with client.session_transaction() as sess:
		assert "over_18" in sess
		# Should be set to current time + 3600 seconds (within reasonable margin)
		current_time = int(time.time())
		assert abs(sess["over_18"] - (current_time + 3600)) < 5


def test_allow_nsfw_with_relative_redirect():
	"""Test /allow_nsfw with relative path redirect - should be prefixed with SITE_FULL"""
	client = util_accounts.create_logged_off_client()

	response = client.post("/allow_nsfw", data={"redir": "/some/path"})

	assert response.status_code == 302
	# Should be prefixed with SITE_FULL (which in tests should be http://localhost)
	assert response.location.endswith("/some/path")
	assert response.location.startswith("http")

	# Verify session was set
	with client.session_transaction() as sess:
		assert "over_18" in sess


def test_allow_nsfw_with_site_full_redirect():
	"""Test /allow_nsfw with full SITE_FULL URL redirect - should redirect directly"""
	from files.helpers.config.environment import SITE_FULL

	client = util_accounts.create_logged_off_client()
	redirect_url = f"{SITE_FULL}/target/page"

	response = client.post("/allow_nsfw", data={"redir": redirect_url})

	assert response.status_code == 302
	assert response.location == redirect_url

	# Verify session was set
	with client.session_transaction() as sess:
		assert "over_18" in sess


def test_allow_nsfw_with_external_redirect():
	"""Test /allow_nsfw with external URL redirect - should fall back to /"""
	client = util_accounts.create_logged_off_client()

	response = client.post("/allow_nsfw", data={"redir": "https://external.example.com/evil"})

	assert response.status_code == 302
	assert response.location == "/"

	# Verify session was set
	with client.session_transaction() as sess:
		assert "over_18" in sess


def test_allow_nsfw_with_empty_redirect():
	"""Test /allow_nsfw with empty redirect parameter - should redirect to /"""
	client = util_accounts.create_logged_off_client()

	response = client.post("/allow_nsfw", data={"redir": ""})

	assert response.status_code == 302
	assert response.location == "/"

	# Verify session was set
	with client.session_transaction() as sess:
		assert "over_18" in sess


def test_allow_nsfw_session_expiry():
	"""Test that the over_18 session is set to expire in 1 hour"""
	client = util_accounts.create_logged_off_client()

	before_time = int(time.time())
	response = client.post("/allow_nsfw")
	after_time = int(time.time())

	assert response.status_code == 302

	with client.session_transaction() as sess:
		session_expiry = sess["over_18"]
		# Should be current time + 3600, within the test execution window
		assert before_time + 3600 <= session_expiry <= after_time + 3600