"""Tests for bot detection and rate limiting functionality."""
import pytest
import time
from . import util_accounts
from . import util
from . import util_submissions


@pytest.fixture(autouse=True)
def enable_rate_limiting_for_bot_tests():
	"""Re-enable rate limiting for these specific bot tests only"""
	from files.__main__ import app, limiter

	# Store original state
	original_config = app.config.get('RATE_LIMITER_ENABLED')
	original_enabled = limiter.enabled

	# Enable rate limiting for these tests
	app.config['RATE_LIMITER_ENABLED'] = True
	limiter.enabled = True

	yield

	# Restore original state after test
	app.config['RATE_LIMITER_ENABLED'] = original_config
	limiter.enabled = original_enabled


def test_bot_hits_rate_limit_faster_than_regular_user():
	"""Test that bots are rate limited at 12/min while regular users have higher limits"""
	bot_client = util_accounts.create_logged_off_client()
	regular_client = util_accounts.create_logged_off_client()

	bot_ua = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
	regular_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

	# Make 15 requests with bot user agent
	bot_responses = []
	for i in range(15):
		response = bot_client.get(
			f"/?t={i}",  # Add query param to avoid caching
			headers={"User-Agent": bot_ua}
		)
		bot_responses.append(response)

	# Make 15 requests with regular user agent
	regular_responses = []
	for i in range(15):
		response = regular_client.get(
			f"/?t={i}",
			headers={"User-Agent": regular_ua}
		)
		regular_responses.append(response)

	# Count successful requests
	bot_successful = len([r for r in bot_responses if r.status_code == 200])
	regular_successful = len([r for r in regular_responses if r.status_code == 200])

	# Bots should be limited to ~12 requests/min
	# Regular users should get more through (they have 30/min default)
	assert bot_successful <= 12, f"Bot should be limited to ~12 requests, got {bot_successful}"
	assert regular_successful > bot_successful, \
		f"Regular user should get more requests through ({regular_successful}) than bot ({bot_successful})"


def test_bot_rate_limited_on_search_posts():
	"""Test that bots hit rate limit on search posts at 12/min"""
	client = util_accounts.create_logged_off_client()

	bot_ua = "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"

	# Make 15 search requests quickly (more than 12/min limit)
	responses = []
	for i in range(15):
		response = client.get(
			f"/search/posts?q=test{i}",
			headers={"User-Agent": bot_ua}
		)
		responses.append(response)

	# Count how many succeeded
	successful = len([r for r in responses if r.status_code == 200])
	rate_limited = len([r for r in responses if r.status_code == 429])

	# Should hit the 12/min limit
	assert successful <= 12, f"Bot should be limited to ~12 search requests, got {successful}"
	assert rate_limited > 0, f"Expected some 429 responses, got {rate_limited}"


def test_bot_rate_limited_on_search_comments():
	"""Test that bots hit rate limit on search comments"""
	client = util_accounts.create_logged_off_client()

	bot_ua = "Mozilla/5.0 (compatible; ClaudeBot/1.0)"

	responses = []
	for i in range(15):
		response = client.get(
			f"/search/comments?q=test{i}",
			headers={"User-Agent": bot_ua}
		)
		responses.append(response)

	successful = len([r for r in responses if r.status_code == 200])
	assert successful <= 12, f"Bot should be limited to ~12 requests on search comments, got {successful}"


def test_bot_rate_limited_on_search_users():
	"""Test that bots hit rate limit on search users"""
	client = util_accounts.create_logged_off_client()

	bot_ua = "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ChatGPT-User/1.0"

	responses = []
	for i in range(15):
		response = client.get(
			f"/search/users?q=user{i}",
			headers={"User-Agent": bot_ua}
		)
		responses.append(response)

	successful = len([r for r in responses if r.status_code == 200])
	assert successful <= 12, f"Bot should be limited to ~12 requests on search users, got {successful}"


def test_multiple_bot_types_all_rate_limited():
	"""Test that different bot user agents are all detected and rate limited"""
	bot_user_agents = [
		"Mozilla/5.0 (compatible; Googlebot/2.1)",
		"Mozilla/5.0 (compatible; bingbot/2.0)",
		"Amazonbot/1.0",
		"Applebot/0.1",
		"PetalBot",
		"SemrushBot/7",
		"Bytespider",
		"DataForSeoBot/1.0",
		"MJ12bot/v1.4.8",
		"OAI-SearchBot/1.0",
		"ChatGPT-User/1.0",
		"ClaudeBot/1.0"
	]

	for bot_ua in bot_user_agents:
		client = util_accounts.create_logged_off_client()

		# Make 15 requests
		responses = []
		for i in range(15):
			response = client.get(
				f"/?bot_test={i}",
				headers={"User-Agent": bot_ua}
			)
			responses.append(response)

		successful = len([r for r in responses if r.status_code == 200])
		# Each bot type should be limited to ~12 requests
		assert successful <= 12, \
			f"Bot '{bot_ua}' should be limited to ~12 requests, got {successful}"


def test_bot_case_insensitive_detection():
	"""Test that bot detection works regardless of case"""
	client = util_accounts.create_logged_off_client()

	# Test with mixed/uppercase bot name
	bot_ua = "Mozilla/5.0 (compatible; GoogleBot/2.1)"  # Note: GoogleBot not googlebot

	responses = []
	for i in range(15):
		response = client.get(
			f"/?case_test={i}",
			headers={"User-Agent": bot_ua}
		)
		responses.append(response)

	successful = len([r for r in responses if r.status_code == 200])
	# Should still be detected as a bot and rate limited
	assert successful <= 12, \
		f"Mixed-case bot name should still be detected and limited, got {successful} successful requests"


def test_regular_user_higher_limit_than_bot():
	"""Test that regular users can make more requests than bots before hitting limits"""
	bot_client = util_accounts.create_logged_off_client()
	regular_client = util_accounts.create_logged_off_client()

	bot_ua = "Mozilla/5.0 (compatible; Googlebot/2.1)"
	regular_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

	# Make 30 requests with each (default limit for regular users is 30/min)
	bot_responses = []
	for i in range(30):
		response = bot_client.get(
			f"/search/posts?q=bottest{i}",
			headers={"User-Agent": bot_ua}
		)
		bot_responses.append(response)

	regular_responses = []
	for i in range(30):
		response = regular_client.get(
			f"/search/posts?q=regulartest{i}",
			headers={"User-Agent": regular_ua}
		)
		regular_responses.append(response)

	bot_successful = len([r for r in bot_responses if r.status_code == 200])
	regular_successful = len([r for r in regular_responses if r.status_code == 200])

	# Bot should hit limit around 12, regular user around 30
	assert bot_successful <= 12, f"Bot should be limited to ~12, got {bot_successful}"
	assert regular_successful > bot_successful, \
		f"Regular user ({regular_successful}) should get more through than bot ({bot_successful})"
	# Regular users should get closer to 30 requests through
	assert regular_successful >= 20, \
		f"Regular user should get at least 20 requests through, got {regular_successful}"


def test_bot_global_and_search_limits_compound():
	"""Test that bots are subject to both global (12/min) and search-specific (12/min) limits"""
	client = util_accounts.create_logged_off_client()

	bot_ua = "Mozilla/5.0 (compatible; bingbot/2.0)"

	# Make a mix of regular and search requests
	responses = []

	# Make 10 regular page requests
	for i in range(10):
		response = client.get(
			f"/?page_test={i}",
			headers={"User-Agent": bot_ua}
		)
		responses.append(('regular', response))

	# Then try to make 10 search requests
	for i in range(10):
		response = client.get(
			f"/search/posts?q=compoundtest{i}",
			headers={"User-Agent": bot_ua}
		)
		responses.append(('search', response))

	# Count successful requests
	total_successful = len([r for label, r in responses if r.status_code == 200])

	# With 12/min global limit, should hit limit before completing all 20 requests
	assert total_successful <= 12, \
		f"Bot should be limited by global 12/min limit across all endpoints, got {total_successful}"
