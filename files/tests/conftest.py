import pytest


@pytest.fixture(scope="session", autouse=True)
def ensure_admin_account():
	"""Ensure an admin account exists before any tests run"""
	from files.__main__ import db_session, app
	from files.classes import User
	from files.tests import util_accounts

	# Check if any admin account already exists
	admin = db_session.query(User).filter(User.admin_level >= 3).first()

	# Create admin account if none exists
	if not admin:
		# Use the standard account creation function
		client, user = util_accounts.create_test_client_and_user(name="admin")
		# Promote to admin
		user.admin_level = 3
		db_session.add(user)
		db_session.commit()

	yield


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