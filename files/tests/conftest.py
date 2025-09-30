import pytest


@pytest.fixture(scope="session", autouse=True)
def ensure_admin_account():
	"""Ensure an admin account exists before any tests run"""
	from files.__main__ import db_session
	from files.classes import User

	# Check if any admin account already exists
	admin = db_session.query(User).filter(User.admin_level >= 3).first()

	# Create admin account if none exists
	if not admin:
		admin = User(
			username="test-admin",
			original_username="test-admin",
			admin_level=3,
			created_utc=0
		)
		db_session.add(admin)
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