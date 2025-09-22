from . import util

from files.__main__ import app, db_session
from files.classes import User
from functools import lru_cache
from time import time, sleep


@lru_cache(maxsize=None)
def create_test_client_and_user(name="user"):
	"""Create a test client with a newly registered user account."""
	client = app.test_client()

	username = f"test-{name}-{str(round(time()))}"
	print(f"Signing up as {username}")

	signup_post_response, signup_get_response = util.post_with_formkey(
		client, "/signup", "/signup",
		data={
			"usernametwo": username,
			"password": "password",
			"password_confirm": "password",
			"email": "",
		}
	)

	assert signup_post_response.status_code == 302
	if "error" in signup_post_response.location:
		# Extract and print the error message for debugging
		from urllib.parse import parse_qs, urlparse
		parsed_url = urlparse(signup_post_response.location)
		error_message = parse_qs(parsed_url.query).get('error', ['Unknown error'])[0]
		print(f"Signup failed for user '{username}': {error_message}")
	assert "error" not in signup_post_response.location

	db = db_session
	user = db.query(User).filter_by(username=username).first()

	assert User == type(user)

	return client, user


def create_logged_off_client():
	"""Create a test client without authentication."""
	return app.test_client()