from . import util_accounts
from . import util


def test_login_get():
	"""Test accessing the login page"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/login")
	assert response.status_code == 200
	assert "login" in response.text.lower()


def test_login_get_with_redirect():
	"""Test login page preserves redirect parameter"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/login?redirect=/rules")
	assert response.status_code == 200
	assert "redirect" in response.text.lower() or "/rules" in response.text


def test_login_post_successful():
	"""Test successful login with valid credentials"""
	# Create a user first (use unique name to avoid affecting cached fixtures)
	client, user = util_accounts.create_test_client_and_user(name="login-test-1")

	# Log out
	client.get("/logout")

	# Now try to log in
	response = client.post("/login", data={
		"username": user.username,
		"password": "password"
	})

	# Should redirect on success
	assert response.status_code == 302
	assert response.location == "/"


def test_login_post_successful_with_redirect():
	"""Test successful login redirects to specified page"""
	# Create a user first (use unique name to avoid affecting cached fixtures)
	client, user = util_accounts.create_test_client_and_user(name="login-test-2")

	# Log out
	client.get("/logout")

	# Now try to log in with redirect
	response = client.post("/login", data={
		"username": user.username,
		"password": "password",
		"redirect": "/rules"
	})

	# Should redirect to the specified page
	assert response.status_code == 302
	assert "/rules" in response.location


def test_login_post_with_at_prefix():
	"""Test login handles @username format"""
	# Create a user first (use unique name to avoid affecting cached fixtures)
	client, user = util_accounts.create_test_client_and_user(name="login-test-3")

	# Log out
	client.get("/logout")

	# Try to log in with @ prefix
	response = client.post("/login", data={
		"username": f"@{user.username}",
		"password": "password"
	})

	# Should redirect on success
	assert response.status_code == 302
	assert response.location == "/"


def test_login_post_wrong_password():
	"""Test login with wrong password fails"""
	# Create a user first (use unique name to avoid affecting cached fixtures)
	client, user = util_accounts.create_test_client_and_user(name="login-test-4")

	# Log out
	client.get("/logout")

	# Try to log in with wrong password
	response = client.post("/login", data={
		"username": user.username,
		"password": "wrongpassword"
	})

	# Should show failed login page
	assert response.status_code == 200
	assert "failed" in response.text.lower() or "incorrect" in response.text.lower()


def test_login_post_nonexistent_user():
	"""Test login with nonexistent username fails"""
	client = util_accounts.create_logged_off_client()

	response = client.post("/login", data={
		"username": "nonexistent_user_12345",
		"password": "password"
	})

	# Should show failed login page
	assert response.status_code == 200
	assert "failed" in response.text.lower() or "incorrect" in response.text.lower()


def test_login_post_missing_username():
	"""Test login without username returns 400"""
	client = util_accounts.create_logged_off_client()

	response = client.post("/login", data={
		"password": "password"
	})

	assert response.status_code == 400




def test_logout_requires_auth():
	"""Test logout endpoint requires authentication"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/logout")
	assert response.status_code == 302
	assert "/login" in response.location


def test_logout():
	"""Test logout endpoint logs user out"""
	# Use a unique name to avoid affecting cached fixtures
	client, user = util_accounts.create_test_client_and_user(name="logout-test")

	# Logout
	response = client.get("/logout")
	assert response.status_code == 302

	# Verify we're logged out by trying to access a protected page
	response = client.get("/submit")
	assert response.status_code == 302
	assert "/login" in response.location


def test_me_requires_auth():
	"""Test /me endpoint requires authentication"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/me")
	assert response.status_code == 302
	assert "/login" in response.location


def test_me_endpoint_exists():
	"""Test /me endpoint exists"""
	client, user = util_accounts.create_test_client_and_user()

	# The endpoint requires auth and will either return JSON or redirect
	response = client.get("/me")
	# Should not be 404
	assert response.status_code != 404


def test_at_me_requires_auth():
	"""Test /@me endpoint requires authentication"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/@me")
	assert response.status_code == 302
	assert "/login" in response.location


def test_at_me_endpoint_exists():
	"""Test /@me endpoint exists"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/@me")
	# Should not be 404
	assert response.status_code != 404


def test_signup_get():
	"""Test accessing the signup page"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/signup")
	# Could be 200 (signups enabled) or 403 (signups disabled)
	assert response.status_code in [200, 403]

	if response.status_code == 200:
		assert "sign" in response.text.lower() and "up" in response.text.lower()


def test_signup_get_with_ref():
	"""Test signup page with referral parameter"""
	# Create a user to be the referrer
	_, referrer = util_accounts.create_test_client_and_user()

	client = util_accounts.create_logged_off_client()

	response = client.get(f"/signup?ref={referrer.username}")
	# Could be 200 (signups enabled) or 403 (signups disabled)
	assert response.status_code in [200, 403]

	if response.status_code == 200:
		# Referrer username should appear in the page
		assert referrer.username in response.text


def test_signup_with_logged_in_user():
	"""Test signup page behavior when user is already logged in"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/signup")
	# Behavior depends on whether signups are enabled:
	# - If enabled and user is logged in: redirects (302) or shows page (200)
	# - If disabled: 403
	assert response.status_code in [200, 302, 403]


def test_forgot_password_get():
	"""Test accessing the forgot password page"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/forgot")
	assert response.status_code == 200
	assert "forgot" in response.text.lower() or "password" in response.text.lower()


def test_forgot_password_post_valid():
	"""Test forgot password with valid username and email"""
	client, user = util_accounts.create_test_client_and_user(name="forgot-test")

	# Store username for later use (email field is deferred)
	username = user.username

	# Log out first
	client.get("/logout")

	# Request password reset (email is optional in signup, so use empty string)
	response = client.post("/forgot", data={
		"username": username,
		"email": "test@example.com"
	})

	assert response.status_code == 200
	assert "email" in response.text.lower()


def test_forgot_password_post_invalid_email():
	"""Test forgot password with invalid email format"""
	client = util_accounts.create_logged_off_client()

	response = client.post("/forgot", data={
		"username": "someuser",
		"email": "not-an-email"
	})

	assert response.status_code == 200
	assert "invalid" in response.text.lower()


def test_forgot_password_post_no_username():
	"""Test forgot password without username returns 400"""
	client = util_accounts.create_logged_off_client()

	response = client.post("/forgot", data={
		"email": "test@example.com"
	})

	assert response.status_code == 400


def test_forgot_password_post_mismatched_user():
	"""Test forgot password with username that doesn't match email"""
	client, user = util_accounts.create_test_client_and_user(name="forgot-mismatch")

	# Store username for later use
	username = user.username

	# Log out first
	client.get("/logout")

	# Request password reset with wrong email
	response = client.post("/forgot", data={
		"username": username,
		"email": "wrongemail@example.com"
	})

	# Should still return success message for security
	assert response.status_code == 200
	assert "email" in response.text.lower()


def test_lost_2fa_get():
	"""Test accessing the lost 2FA page"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/lost_2fa")
	assert response.status_code == 200
	assert "2fa" in response.text.lower() or "two" in response.text.lower()


def test_request_2fa_disable_no_user():
	"""Test 2FA disable request with nonexistent user"""
	client = util_accounts.create_logged_off_client()

	response = client.post("/request_2fa_disable", data={
		"username": "nonexistentuser123",
		"email": "test@example.com",
		"password": "password"
	})

	# Should return generic success message for security
	assert response.status_code == 200
	assert "email" in response.text.lower() or "received" in response.text.lower()


def test_request_2fa_disable_no_2fa():
	"""Test 2FA disable request for user without 2FA"""
	client, user = util_accounts.create_test_client_and_user(name="2fa-disable-test")

	# Store username for later use
	username = user.username

	# User doesn't have 2FA enabled, so should get generic message
	response = client.post("/request_2fa_disable", data={
		"username": username,
		"email": "test@example.com",
		"password": "password"
	})

	assert response.status_code == 200
	assert "removal" in response.text.lower() or "received" in response.text.lower()


def test_signup_password_mismatch():
	"""Test signup with mismatched passwords"""
	client = util_accounts.create_logged_off_client()

	signup_post_response, signup_get_response = util.post_with_formkey(
		client, "/signup",
		data={
			"usernametwo": "testuser123",
			"password": "password123",
			"password_confirm": "differentpassword",
			"email": "",
		}
	)

	# Should redirect back to signup with error
	assert signup_post_response.status_code == 302
	assert "error" in signup_post_response.location
	assert "password" in signup_post_response.location.lower()


def test_signup_invalid_username():
	"""Test signup with invalid username characters"""
	client = util_accounts.create_logged_off_client()

	signup_post_response, signup_get_response = util.post_with_formkey(
		client, "/signup",
		data={
			"usernametwo": "invalid username!@#",
			"password": "password123",
			"password_confirm": "password123",
			"email": "",
		}
	)

	# Should redirect back to signup with error
	assert signup_post_response.status_code == 302
	assert "error" in signup_post_response.location
	assert "username" in signup_post_response.location.lower()


def test_signup_short_password():
	"""Test signup with password that's too short"""
	client = util_accounts.create_logged_off_client()

	signup_post_response, signup_get_response = util.post_with_formkey(
		client, "/signup",
		data={
			"usernametwo": "testuser456",
			"password": "short",
			"password_confirm": "short",
			"email": "",
		}
	)

	# Should redirect back to signup with error
	assert signup_post_response.status_code == 302
	assert "error" in signup_post_response.location
	assert "password" in signup_post_response.location.lower()


def test_signup_invalid_email():
	"""Test signup with invalid email format"""
	client = util_accounts.create_logged_off_client()

	signup_post_response, signup_get_response = util.post_with_formkey(
		client, "/signup",
		data={
			"usernametwo": "testuser789",
			"password": "password123",
			"password_confirm": "password123",
			"email": "not-an-email",
		}
	)

	# Should redirect back to signup with error
	assert signup_post_response.status_code == 302
	assert "error" in signup_post_response.location
	assert "email" in signup_post_response.location.lower()


def test_signup_existing_username():
	"""Test signup with username that already exists"""
	# Create a user first
	_, existing_user = util_accounts.create_test_client_and_user(name="existing")

	# Try to create another user with the same username
	client = util_accounts.create_logged_off_client()

	signup_post_response, signup_get_response = util.post_with_formkey(
		client, "/signup",
		data={
			"usernametwo": existing_user.username,
			"password": "password123",
			"password_confirm": "password123",
			"email": "",
		}
	)

	# Should redirect back to signup with error
	assert signup_post_response.status_code == 302
	assert "error" in signup_post_response.location
	assert "exists" in signup_post_response.location.lower() or "username" in signup_post_response.location.lower()


def test_reset_get():
	"""Test GET /reset route"""
	client = util_accounts.create_logged_off_client()

	# Should require token parameter
	response = client.get("/reset")
	# Will likely redirect or show error without token
	assert response.status_code in [200, 302, 400, 404]


def test_reset_2fa_get():
	"""Test GET /reset_2fa route"""
	client = util_accounts.create_logged_off_client()

	# Should require token parameter
	response = client.get("/reset_2fa")
	# Will likely redirect or show error without token
	assert response.status_code in [200, 302, 400, 404]

def _set_cookie_headers(response, name):
	return [h for h in response.headers.getlist("Set-Cookie") if h.startswith(f"{name}=")]


def test_logged_in_cookie_set_on_login():
	"""The login response sets the logged_in marker with the session cookie's attributes, and later responses don't re-send it."""
	from files.helpers.config.const import LOGGED_IN_COOKIE
	client, user = util_accounts.create_test_client_and_user(name="lic-set")
	client.get("/logout")
	assert client.get_cookie(LOGGED_IN_COOKIE) is None

	response = client.post("/login", data={"username": user.username, "password": "password"})
	assert response.status_code == 302
	header = _set_cookie_headers(response, LOGGED_IN_COOKIE)[0]
	assert "HttpOnly" in header
	assert "SameSite=Lax" in header
	assert client.get_cookie(LOGGED_IN_COOKIE).value == "1"

	response = client.get("/")
	assert response.status_code == 200
	assert _set_cookie_headers(response, LOGGED_IN_COOKIE) == []


def test_logged_in_cookie_cleared_on_logout():
	"""The logout response itself deletes the marker, and later responses don't bring it back."""
	from files.helpers.config.const import LOGGED_IN_COOKIE
	client, user = util_accounts.create_test_client_and_user(name="lic-clear")

	client.get("/")
	assert client.get_cookie(LOGGED_IN_COOKIE) is not None

	response = client.get("/logout")
	assert response.status_code == 302
	deletions = _set_cookie_headers(response, LOGGED_IN_COOKIE)
	assert len(deletions) == 1
	assert "Max-Age=0" in deletions[0]
	assert client.get_cookie(LOGGED_IN_COOKIE) is None

	response = client.get("/")
	assert _set_cookie_headers(response, LOGGED_IN_COOKIE) == []
	assert client.get_cookie(LOGGED_IN_COOKIE) is None


def test_logged_in_cookie_absent_for_anonymous():
	"""An anonymous visitor never receives the marker, even though they get a session cookie."""
	from files.helpers.config.const import LOGGED_IN_COOKIE
	client = util_accounts.create_logged_off_client()

	response = client.get("/")
	assert response.status_code == 200
	assert _set_cookie_headers(response, LOGGED_IN_COOKIE) == []
	assert client.get_cookie(LOGGED_IN_COOKIE) is None


def test_logged_in_cookie_not_resent_by_static_routes():
	"""Once the jar has the marker, static asset responses must not keep re-sending it."""
	from files.helpers.config.const import LOGGED_IN_COOKIE
	client, user = util_accounts.create_test_client_and_user(name="lic-static")

	client.get("/")
	assert client.get_cookie(LOGGED_IN_COOKIE) is not None

	response = client.get("/assets/robots.txt")
	assert response.status_code == 200
	assert _set_cookie_headers(response, LOGGED_IN_COOKIE) == []


def test_static_routes_do_not_start_varying_on_cookie():
	"""The marker logic must not touch the session on requests that never did, or every static response would grow Vary: Cookie and defeat asset caching."""
	client = util_accounts.create_logged_off_client()

	response = client.get("/assets/robots.txt")
	assert response.status_code == 200
	assert "Cookie" not in response.vary
