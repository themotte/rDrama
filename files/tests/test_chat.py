"""Tests for chat routes."""
from . import util_accounts


def test_chat_route_not_available_in_themotte_service():
	"""Test /chat route is not available in THEMOTTE service mode"""
	client = util_accounts.create_logged_off_client()

	# Chat routes are only available in CHAT service mode
	# In THEMOTTE mode (which tests run in), it should return 404
	response = client.get("/chat")
	assert response.status_code == 404
