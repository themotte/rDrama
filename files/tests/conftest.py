import pytest


@pytest.fixture(autouse=True)
def disable_rate_limiting():
	"""Automatically disable rate limiting for all tests"""
	from files.__main__ import app, limiter

	# Store original state
	original_config = app.config.get('RATE_LIMITER_ENABLED')
	original_enabled = limiter.enabled

	# Disable rate limiting
	app.config['RATE_LIMITER_ENABLED'] = False
	limiter.enabled = False

	yield

	# Restore original state after test
	app.config['RATE_LIMITER_ENABLED'] = original_config
	limiter.enabled = original_enabled