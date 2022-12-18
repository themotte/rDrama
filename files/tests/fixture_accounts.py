
from . import util

from bs4 import BeautifulSoup
from files.__main__ import app
from functools import lru_cache
import pytest
from time import time, sleep

class AccountsFixture:
	@lru_cache(maxsize=None)
	def client_for_account(self, name = "default"):

		client = app.test_client()

		signup_get_response = client.get("/signup")
		assert signup_get_response.status_code == 200
		soup = BeautifulSoup(signup_get_response.text, 'html.parser')
		# these hidden input values seem to be used for anti-bot purposes and need to be submitted
		form_timestamp = next(tag for tag in soup.find_all("input") if tag.get("name") == "now").get("value")

		username = f"test-{name}-{str(round(time()))}"
		print(f"Signing up as {username}")
		
		signup_post_response = client.post("/signup", data={
			"username": username,
			"password": "password",
			"password_confirm": "password",
			"email": "",
			"formkey": util.formkey_from(signup_get_response.text),
			"now": form_timestamp
		})
		assert signup_post_response.status_code == 302
		assert "error" not in signup_post_response.location

		return client
	
	def logged_off(self):
		return app.test_client()

@pytest.fixture(scope="session")
def accounts():
	return AccountsFixture()
