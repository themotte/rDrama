from files.tests import testenv

testenv.configure()

import pytest
import traceback
import warnings

NEW_TIER_DIRS = ("spec", "internal")


def _is_new_tier(item):
	return any(part in NEW_TIER_DIRS for part in item.path.relative_to(testenv.REPO_ROOT / "files" / "tests").parts[:-1])


def pytest_configure(config):
	# xdist sets "load" when -n is given without --dist; its workers run with "no"
	if config.getoption("dist", "no") not in ("no", "loadgroup"):
		raise pytest.UsageError("the legacy tests must run together in one worker: add --dist loadgroup")


def pytest_sessionstart(session):
	# A controller handing tests to xdist workers runs none itself; each worker builds its own database
	if not session.config.pluginmanager.hasplugin("dsession"):
		testenv.build_database()


@pytest.hookimpl(tryfirst=True)  # xdist reads the group marks in its own hook, which must see them
def pytest_collection_modifyitems(config, items):
	# The legacy tests depend on state accumulated across the run (cached users, process-wide patches), which the new tiers' per-test reset wipes; run the legacy ones first, and under xdist all in one worker, which loadgroup scheduling starts on them
	items.sort(key=_is_new_tier)
	legacy = [item for item in items if not _is_new_tier(item)]
	for item in legacy:
		item.add_marker(pytest.mark.xdist_group("legacy"))
	if legacy and testenv.WORKER and not config.option.loadgroup:
		raise pytest.UsageError("the legacy tests must run together in one worker: add --dist loadgroup")


class LazyLoadWarning(UserWarning):
	"""Emitted when a SQLAlchemy lazy load is detected during tests.

	Lazy loads indicate a missing eagerly-loaded relationship, which can cause
	N+1 query performance issues in production. To promote these to errors, run
	tests with: pytest -W error::files.tests.conftest.LazyLoadWarning
	"""
	pass


_legacy_admin_ensured = False


@pytest.fixture(autouse=True)
def ensure_admin_account(request):
	"""Ensure an admin account exists before the first legacy test runs"""
	global _legacy_admin_ensured
	if _legacy_admin_ensured or _is_new_tier(request.node):
		return
	_legacy_admin_ensured = True

	from files.__main__ import db_session
	from files.classes import User
	from files.tests import util_accounts

	if not db_session.query(User).filter(User.admin_level >= 3).first():
		util_accounts.create_test_client_and_admin(3, name="admin")


@pytest.fixture(scope="session", autouse=True)
def warn_on_lazy_loads():
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

		# We only care about N+1s on read paths. Mutation handlers
		# (POST/PUT/PATCH/DELETE) commonly do one cheap post-commit reload of
		# the row they just wrote; that's noise, not an N+1. Loads outside a
		# request context (helpers, background work) are still reported.
		from flask import has_request_context, request
		if has_request_context() and request.method not in ("GET", "HEAD"):
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
def rollback_dirty_session(request):
	"""Roll back the shared db_session after each legacy test if it's dirty.

	Tests that manipulate db_session directly (outside of Flask request
	context) can leave it in a "needs rollback" state on failure, which
	cascades PendingRollbackError into every subsequent test.
	"""
	yield
	if _is_new_tier(request.node):
		return
	from files.__main__ import db_session
	if db_session.registry.has():
		db_session.rollback()
