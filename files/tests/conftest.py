from files.tests import testenv

testenv.configure()

import os
import traceback
import warnings

import pytest

from files.tests import affordances, route_coverage

NEW_TIER_DIRS = ("spec", "internal")

# The spec tier against the site running in its own processes (spec/harness/backend_process.py), started by these commands unless the runner names others
PROCESS_BACKEND = os.environ.get("RDRAMA_SPEC_BACKEND") == "process"
if PROCESS_BACKEND:
	os.environ.setdefault("RDRAMA_SPEC_SERVER", "gunicorn files.tests.process_server:application -k gthread --threads 4 -w 1 -b 127.0.0.1:{port} --access-logfile - --error-logfile -")
	os.environ.setdefault("RDRAMA_SPEC_CLI", "python3 -m files.tests.command")
	os.environ.setdefault("RDRAMA_SPEC_SCHEDULER", "python3 -m files.tests.scheduler_pass {at}")


def _is_new_tier(item):
	return any(part in NEW_TIER_DIRS for part in item.path.relative_to(testenv.REPO_ROOT / "files" / "tests").parts[:-1])


def pytest_configure(config):
	# xdist sets "load" when -n is given without --dist; its workers run with "no"
	if config.getoption("dist", "no") not in ("no", "loadgroup"):
		raise pytest.UsageError("the legacy tests must run together in one worker: add --dist loadgroup")
	# A controller handing tests to xdist workers runs none itself; each worker builds its own database. Built here because pytest replays pytest_configure for a conftest it loads late (as it does without a path below files/tests), unlike pytest_sessionstart.
	if config.getoption("dist", "no") == "no" or config.getoption("collectonly"):
		# Registered first, so a half-built database goes too
		config.add_cleanup(testenv.drop_database)
		testenv.build_database()


@pytest.hookimpl(tryfirst=True)  # xdist reads the group marks in its own hook, which must see them
def pytest_collection_modifyitems(config, items):
	# The legacy tests depend on state accumulated across the run (cached users, process-wide patches), which the new tiers' per-test reset wipes; run the legacy ones first, and under xdist all in one worker, which loadgroup scheduling starts on them
	if PROCESS_BACKEND and (outside := [item.nodeid for item in items if "spec" not in item.path.relative_to(testenv.REPO_ROOT / "files" / "tests").parts[:1]]):
		raise pytest.UsageError(f"RDRAMA_SPEC_BACKEND=process runs only the spec tier, not {outside[0]} and {len(outside) - 1} more")
	items.sort(key=_is_new_tier)
	legacy = [item for item in items if not _is_new_tier(item)]
	for item in legacy:
		item.add_marker(pytest.mark.xdist_group("legacy"))
	if legacy and testenv.WORKER and not config.option.loadgroup:
		raise pytest.UsageError("the legacy tests must run together in one worker: add --dist loadgroup")


# Route coverage (route_coverage.py) and what pages offer (affordances.py), checked when a run collected every spec test and passed
_coverage = {"deselected": 0, "complete": True, "seen": set(), "unrequested": None, "affordances": [], "page_problems": {}, "map_unwritten": False}


def pytest_deselected(items):
	_coverage["deselected"] += len(items)


def pytest_collection_finish(session):
	# Both checks watch the app in the test's own process
	_coverage["complete"] = not PROCESS_BACKEND and not session.config.getoption("collectonly") and route_coverage.collected_whole_spec({item.path for item in session.items}, _coverage["deselected"], session.config.args)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
	if PROCESS_BACKEND:
		return (yield)
	route_coverage.start(item.path)
	if _coverage["complete"]: affordances.start(item.path)
	try:
		return (yield)
	finally:
		route_coverage.stop()
		affordances.stop()


@pytest.hookimpl(optionalhook=True)
def pytest_testnodedown(node, error):
	# A worker that crashed sends no output
	output = getattr(node, "workeroutput", {}).get("route_coverage")
	if output is None:
		_coverage["complete"] = False
		return
	_coverage["complete"] &= output["complete"]
	_coverage["seen"] |= {tuple(pair) for pair in output["seen"]}
	_coverage["affordances"].append(node.workeroutput["affordances"])


def pytest_sessionfinish(session, exitstatus):
	if hasattr(session.config, "workeroutput"):
		session.config.workeroutput["route_coverage"] = {"complete": _coverage["complete"], "seen": sorted(route_coverage.seen())}
		session.config.workeroutput["affordances"] = affordances.output()
		return
	_coverage["map_unwritten"] = bool(os.environ.get("RDRAMA_AFFORDANCES_OUT"))
	if exitstatus != pytest.ExitCode.OK or not _coverage["complete"]:
		return
	_coverage["unrequested"] = route_coverage.unrequested(_coverage["seen"] | route_coverage.seen())
	offered = affordances.merge([*_coverage["affordances"], affordances.output()])
	_coverage["page_problems"] = affordances.problems(offered)
	if _coverage["unrequested"] or _coverage["page_problems"]:
		session.exitstatus = pytest.ExitCode.TESTS_FAILED
	elif os.environ.get("RDRAMA_AFFORDANCES_OUT"):
		with open(os.environ["RDRAMA_AFFORDANCES_OUT"], "w") as out:
			out.write(affordances.table(offered["rows"]))
		_coverage["map_unwritten"] = False


def pytest_terminal_summary(terminalreporter):
	if PROCESS_BACKEND:
		terminalreporter.write_line("The site ran in its own processes, so route coverage and what pages offer weren't checked (they watch it in-process)", yellow=True)
	if _coverage["unrequested"]:
		terminalreporter.section("routes no spec test gets past the gate of", red=True)
		for route in _coverage["unrequested"]:
			terminalreporter.write_line(route)
		terminalreporter.write_line("(the run fails: every route needs a spec test outside spec/routes/ that the gate lets through)", red=True)
	for heading, problems in _coverage["page_problems"].items():
		terminalreporter.section(heading, red=True)
		for problem in problems:
			terminalreporter.write_line(problem)
		terminalreporter.write_line("(the run fails: pages may lead only to routes, and every script call they make must be classified in affordances.py)", red=True)
	if _coverage["map_unwritten"]:
		terminalreporter.write_line("RDRAMA_AFFORDANCES_OUT is set, but the map is written only by a passing run that collected the whole spec tier", yellow=True)


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
