import pytest
import os
import traceback
import warnings


class LazyLoadWarning(UserWarning):
	"""Emitted when a SQLAlchemy lazy load is detected during tests.

	Lazy loads indicate a missing eagerly-loaded relationship, which can cause
	N+1 query performance issues in production. To promote these to errors, run
	tests with: pytest -W error::files.tests.conftest.LazyLoadWarning
	"""
	pass


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
	"""Set up test environment before any tests run"""
	# Mark that we're in test mode so password hashing can be faster
	os.environ['RDRAMA_TESTING'] = '1'
	yield
	# Clean up after all tests
	os.environ.pop('RDRAMA_TESTING', None)


@pytest.fixture(scope="session", autouse=True)
def ensure_admin_account(setup_test_environment):
	"""Ensure an admin account exists before any tests run"""
	from files.__main__ import db_session, app
	from files.classes import User
	from files.tests import util_accounts

	# Check if any admin account already exists
	admin = db_session.query(User).filter(User.admin_level >= 3).first()

	# Create admin account if none exists
	if not admin:
		# Use the standard account creation function
		client, user = util_accounts.create_test_client_and_admin(3, name="admin")

	yield


@pytest.fixture(scope="session", autouse=True)
def warn_on_lazy_loads(setup_test_environment):
	"""Detect SQLAlchemy lazy loads and emit warnings.

	When an ORM attribute is accessed that wasn't eagerly loaded, SQLAlchemy
	fires a separate query (a "lazy load"). This is the root cause of N+1
	query issues. This fixture hooks into SQLAlchemy's ORM execution events
	to detect these and emit warnings with the source location.

	Note: this detects lazy="select" (the default) loads. It does NOT detect
	lazy="dynamic" relationships, which return a Query object on access
	rather than firing an immediate load.
	"""
	from sqlalchemy import event
	from sqlalchemy.orm import Session

	@event.listens_for(Session, "do_orm_execute")
	def on_orm_execute(orm_execute_state):
		if not orm_execute_state.is_select:
			return
		if orm_execute_state.lazy_loaded_from is None:
			return

		state = orm_execute_state.lazy_loaded_from
		parent_cls = state.class_.__name__

		frames = traceback.extract_stack()
		app_frames = [
			f for f in frames
			if '/files/' in f.filename
			and '/site-packages/' not in f.filename
			and '/conftest.py' not in f.filename
		]
		if app_frames:
			f = app_frames[-1]
			location = f"{f.filename}:{f.lineno} in {f.name}"
		else:
			location = "(no application frame)"

		warnings.warn(
			f"Lazy load on {parent_cls} instance at {location}",
			LazyLoadWarning,
			stacklevel=1,
		)

	yield

	event.remove(Session, "do_orm_execute", on_orm_execute)


@pytest.fixture(autouse=True)
def rollback_dirty_session():
	"""Roll back the shared db_session after each test if it's dirty.

	Tests that manipulate db_session directly (outside of Flask request
	context) can leave it in a "needs rollback" state on failure, which
	cascades PendingRollbackError into every subsequent test.
	"""
	yield
	from files.__main__ import db_session
	if db_session.registry.has():
		db_session.rollback()


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