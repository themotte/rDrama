
from . import util

from bs4 import BeautifulSoup
from files.__main__ import app
import pytest
from time import time, sleep

class AccountsFixture:
	accounts = {}

	def account(self, name = "default"):
		if name in self.accounts:
			return self.accounts[name]

		client = app.test_client()

		signup_get_response = client.get("/signup")
		assert signup_get_response.status_code == 200
		soup = BeautifulSoup(signup_get_response.text, 'html.parser')
		# these hidden input values seem to be used for anti-bot purposes and need to be submitted
		form_timestamp = next(tag for tag in soup.find_all("input") if tag.get("name") == "now").get("value")

		username = f"test-{name}-{str(round(time()))}"
		print(f"Signing up as {username}")

		sleep(5) # too-fast submissions are rejected (bot check?)
		
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

		self.accounts[name] = client

		return client
	
	def logged_off(self):
		return app.test_client()

@pytest.fixture(scope="session")
def accounts():
	return AccountsFixture()
