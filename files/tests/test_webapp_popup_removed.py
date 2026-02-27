"""Tests verifying the 'Install the Webapp' popup has been removed (#671).

The popup was removed because it covered the notification bell on mobile
and provided questionable value. These tests verify:
1. The homepage no longer contains popup markup
2. The dismiss_mobile_tip route no longer exists
"""
from . import util_accounts
from . import util


def test_homepage_no_mobile_prompt():
	"""Test that the homepage does not contain the mobile-prompt popup"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/")
	assert response.status_code == 200
	assert "mobile-prompt" not in response.text


def test_homepage_no_mobile_prompt_logged_in():
	"""Test that the homepage does not contain the mobile-prompt popup when logged in"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/")
	assert response.status_code == 200
	assert "mobile-prompt" not in response.text


def test_homepage_no_install_webapp_text():
	"""Test that the homepage does not contain 'Install the' webapp text"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/")
	assert response.status_code == 200
	assert "Install the" not in response.text


def test_dismiss_mobile_tip_route_removed():
	"""Test that POST /dismiss_mobile_tip route no longer exists"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/dismiss_mobile_tip",
		data={}
	)
	assert response.status_code == 404
