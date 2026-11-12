import os

# The harness drives an implementation in its own processes by default; this suite drives rDrama in-process unless told otherwise
os.environ.setdefault("RDRAMA_SPEC_BACKEND", "inprocess")

from files.tests import testenv

testenv.configure()

import traceback
import warnings

import pytest

from files.tests import affordances, router_check

# The spec tier against the site running in its own processes (spec/harness/backend_process.py), started by these commands unless the runner names others
PROCESS_BACKEND = os.environ["RDRAMA_SPEC_BACKEND"] != "inprocess"
if PROCESS_BACKEND:
	os.environ.setdefault("RDRAMA_SPEC_SERVER", "gunicorn files.tests.process_server:application -k gthread --threads 4 -w 1 -b 127.0.0.1:{port} --access-logfile - --error-logfile -")
	os.environ.setdefault("RDRAMA_SPEC_CLI", "python3 -m files.tests.command")
	os.environ.setdefault("RDRAMA_SPEC_SCHEDULER", "python3 -m files.tests.scheduler_pass {at}")


def _spec_plugin():
	# Imported once registered, so that pytest's assertion rewriting has it first
	from files.tests.spec.harness import plugin
	return plugin


def pytest_configure(config):
	# The spec's own plugin, registered here rather than by pytest_plugins, which a conftest loaded late (as it is without a path below files/tests) may not use
	config.pluginmanager.import_plugin("files.tests.spec.harness.plugin")
	if PROCESS_BACKEND and os.environ.get("RDRAMA_AFFORDANCES_OUT"):
		raise pytest.UsageError("RDRAMA_AFFORDANCES_OUT needs the in-process backend: the map's script rows come from watching the app")
	# A controller handing tests to xdist workers runs none itself; each worker builds its own database. Built here because pytest replays pytest_configure for a conftest it loads late (as it does without a path below files/tests), unlike pytest_sessionstart.
	if config.getoption("dist", "no") == "no" or config.getoption("collectonly"):
		# Registered first, so a half-built database goes too
		config.add_cleanup(testenv.drop_database)
		testenv.build_database()


def pytest_collection_modifyitems(config, items):
	if PROCESS_BACKEND and (outside := [item.nodeid for item in items if "spec" not in item.path.relative_to(testenv.REPO_ROOT / "files" / "tests").parts[:1]]):
		raise pytest.UsageError(f"RDRAMA_SPEC_BACKEND=process runs only the spec tier, not {outside[0]} and {len(outside) - 1} more")


# What only rDrama's own runs check, beside the spec plugin's whole-run checks and on the same whole runs: the harness's route matching against the router (router_check.py) and what pages offer, scripts included (affordances.py), with the map it writes
_checks = {"ran": False, "mismatches": set(), "affordances": [], "problems": {}, "map_unwritten": False}


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
	if PROCESS_BACKEND or not item.path.is_relative_to(testenv.REPO_ROOT / "files" / "tests" / "spec"):
		return (yield)
	router_check.connect()
	if _spec_plugin().whole_run(): affordances.start(item.path)
	try:
		return (yield)
	finally:
		affordances.stop()


@pytest.hookimpl(optionalhook=True)
def pytest_testnodedown(node, error):
	# A worker that crashed sends no output, which the spec plugin counts against the run
	output = getattr(node, "workeroutput", {}).get("rdrama_checks")
	if output is not None:
		_checks["mismatches"] |= set(output["mismatches"])
		_checks["affordances"].append(output["affordances"])


# After the spec plugin's, whose verdict is then in session.exitstatus; these checks run on the tests' own verdict, `exitstatus`, so that both kinds of finding show
@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
	if hasattr(session.config, "workeroutput"):
		session.config.workeroutput["rdrama_checks"] = {"mismatches": sorted(router_check.mismatches()), "affordances": affordances.output()}
		return
	_checks["map_unwritten"] = bool(os.environ.get("RDRAMA_AFFORDANCES_OUT"))
	if exitstatus != pytest.ExitCode.OK or not _spec_plugin().whole_run():
		return
	_checks["ran"] = True
	_checks["mismatches"] |= router_check.mismatches()
	offered = affordances.merge([*_checks["affordances"], affordances.output()])
	_checks["problems"] = affordances.problems(offered)
	if _checks["mismatches"] or _checks["problems"]:
		session.exitstatus = pytest.ExitCode.TESTS_FAILED
	elif os.environ.get("RDRAMA_AFFORDANCES_OUT") and session.exitstatus == pytest.ExitCode.OK:
		with open(os.environ["RDRAMA_AFFORDANCES_OUT"], "w") as out:
			out.write(affordances.table(offered["rows"]))
		_checks["map_unwritten"] = False


def pytest_terminal_summary(terminalreporter):
	if PROCESS_BACKEND:
		terminalreporter.write_line("The site ran in its own processes: route coverage and where pages lead were checked from what the harness saw; script calls and the affordance map are checked only in-process", yellow=True)
	if _checks["mismatches"] and _checks["ran"]:
		terminalreporter.section("requests the harness matches to another row than the router", red=True)
		for mismatch in sorted(_checks["mismatches"]):
			terminalreporter.write_line(mismatch)
		terminalreporter.write_line("(the run fails: spec/harness/routes.py match() must answer as the router does)", red=True)
	for heading, problems in _checks["problems"].items():
		terminalreporter.section(heading, red=True)
		for problem in problems:
			terminalreporter.write_line(problem)
		terminalreporter.write_line("(the run fails: every script call pages make must be classified in affordances.py, and lead to a route)", red=True)
	if _checks["map_unwritten"]:
		terminalreporter.write_line("RDRAMA_AFFORDANCES_OUT is set, but the map is written only by a passing run that collected the whole spec tier", yellow=True)


class LazyLoadWarning(UserWarning):
	"""Emitted when a SQLAlchemy lazy load is detected during tests.

	Lazy loads indicate a missing eagerly-loaded relationship, which can cause
	N+1 query performance issues in production. To promote these to errors, run
	tests with: pytest -W error::files.tests.conftest.LazyLoadWarning
	"""
	pass


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
