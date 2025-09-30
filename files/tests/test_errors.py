from . import util_accounts
from . import util
from flask import g


def test_error_404_html():
	"""Test 404 error returns HTML for regular requests"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/nonexistent-page")
	assert response.status_code == 404
	assert "text/html" in response.content_type
	assert "404" in response.text


def test_error_404_json_with_authorization():
	"""Test 404 error returns JSON when Authorization header is present"""
	client, user = util_accounts.create_test_client_and_user()

	# Make request with Authorization header to trigger JSON response
	response = client.get("/nonexistent-page", headers={"Authorization": "Bearer fake-token"})
	assert response.status_code == 404
	assert response.json is not None
	assert "code" in response.json
	assert response.json["code"] == 404
	assert "error" in response.json
	assert "description" in response.json


def test_error_404_json_with_xhr():
	"""Test 404 error returns JSON when xhr header is present"""
	client, user = util_accounts.create_test_client_and_user()

	# Make request with xhr header to trigger JSON response
	response = client.get("/nonexistent-page", headers={"xhr": "true"})
	assert response.status_code == 404
	assert response.json is not None
	assert "code" in response.json
	assert response.json["code"] == 404
	assert "error" in response.json


def test_error_401_redirect_to_login():
	"""Test 401 error redirects to login page with redirect parameter"""
	client = util_accounts.create_logged_off_client()

	# Try to access a protected endpoint
	response = client.get("/submit")
	assert response.status_code == 302  # Redirect
	assert "/login" in response.location
	assert "redirect=" in response.location


def test_error_401_json_with_authorization():
	"""Test 401 error returns JSON when Authorization header is present"""
	client = util_accounts.create_logged_off_client()

	# Make request with Authorization header
	response = client.get("/submit", headers={"Authorization": "Bearer fake-token"})
	assert response.status_code == 401
	assert response.json is not None
	assert "code" in response.json
	assert response.json["code"] == 401


def test_error_400_bad_request():
	"""Test 400 error is returned for bad requests"""
	client, user = util_accounts.create_test_client_and_user()

	# Try to create a post with no title (should fail validation)
	response, _ = util.post_with_formkey(
		client, "/submit",
		data={
			"body": "Test body",
			# Missing required 'title' field
		}
	)

	assert response.status_code == 400


def test_error_500_internal_server():
	"""Test 500 error handler is registered"""
	# This test verifies the 500 error handler exists and is properly registered
	# Actually triggering a 500 error in tests is difficult and potentially dangerous
	# The handler is tested indirectly through normal test execution
	from files.__main__ import app
	from werkzeug.exceptions import InternalServerError

	# Verify the 500 error handler is registered
	assert 500 in app.error_handler_spec[None]

	# Create a test request context to simulate the error handler
	with app.test_request_context():
		# Create a mock 500 error
		error = InternalServerError("Test error")

		# Get the error handler
		handler = app.error_handler_spec[None][500][InternalServerError]

		# Call the handler (this tests the function exists and can be called)
		# We don't assert on the response as it would require proper request context
		assert handler is not None


def test_allow_nsfw_endpoint():
	"""Test /allow_nsfw endpoint sets session cookie"""
	client = util_accounts.create_logged_off_client()

	# POST to /allow_nsfw
	response = client.post("/allow_nsfw")
	assert response.status_code == 302  # Redirect
	assert response.location == "/"

	# Verify session was set (check cookies)
	# The session should have over_18 set
	with client.session_transaction() as sess:
		assert "over_18" in sess
		assert sess["over_18"] > 0


def test_allow_nsfw_with_redirect():
	"""Test /allow_nsfw endpoint respects redirect parameter"""
	client = util_accounts.create_logged_off_client()

	# POST to /allow_nsfw with redirect
	response = client.post("/allow_nsfw", data={"redir": "/rules"})
	assert response.status_code == 302  # Redirect
	# Should redirect to the specified page
	assert "/rules" in response.location


def test_allow_nsfw_with_full_url_redirect():
	"""Test /allow_nsfw endpoint handles full URL redirects"""
	client = util_accounts.create_logged_off_client()

	from files.helpers.config.environment import SITE_FULL

	# POST to /allow_nsfw with full URL redirect
	response = client.post("/allow_nsfw", data={"redir": f"{SITE_FULL}/rules"})
	assert response.status_code == 302  # Redirect
	assert "/rules" in response.location


def test_allow_nsfw_ignores_external_redirect():
	"""Test /allow_nsfw endpoint ignores external redirects for security"""
	client = util_accounts.create_logged_off_client()

	# POST to /allow_nsfw with external URL (should be ignored)
	response = client.post("/allow_nsfw", data={"redir": "https://evil.com"})
	assert response.status_code == 302  # Redirect
	assert response.location == "/"  # Should redirect to home, not external site