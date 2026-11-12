'''
The spec tier's pytest plugin: what a run of the spec does around its tests and at its end, whatever implementation it drives. A runner loads it as files.tests.spec.harness.plugin: by `pytest_plugins` in its rootdir conftest, by `config.pluginmanager.import_plugin` in its `pytest_configure`, or by `-p files.tests.spec.harness.plugin` when the directory holding `files/` is already on sys.path as pytest starts (`python -m pytest` from it, or PYTHONPATH). The spec's own conftest refuses to run a test without it.
- The `profile` mark (config.PROFILES): registered, and a name it doesn't list refused. When the site runs in its own processes, each profile's tests are kept to one pytest-xdist worker (an xdist_group per profile, for `--dist loadgroup`), since a worker starts a site for each profile it runs.
- The run record (run_record.py) around each spec test's call phase, not its fixtures.
- At the end of a passing run that collected the whole spec tier (coverage.collected_whole_spec), with what every worker saw merged: route coverage (coverage.py) and where pages lead (pages.py). The run fails on anything they report. A worker that crashed sends nothing, which leaves the run incomplete, so these checks don't run.
'''
import pytest

from files.tests.spec.harness import backend, coverage, pages, run_record
from files.tests.spec.harness.config import PROFILES

_run: dict = {}


def whole_run() -> bool:
	'''Whether the run counts as whole so far: once collected, that it collected the whole spec tier; on an xdist controller, that every worker that has reported so far did, and none crashed.'''
	return _run["complete"]


def pytest_configure(config):
	_run.update(deselected=0, complete=True, seen=set(), pages=[], unrequested=[], page_problems={})
	config.addinivalue_line("markers", "profile(name): runs the test with the site in that deployment profile (spec/harness/config.py PROFILES)")


@pytest.hookimpl(tryfirst=True)  # xdist reads the group marks in its own hook, which must see them
def pytest_collection_modifyitems(config, items):
	for item in items:
		if not (profile := item.get_closest_marker("profile")):
			continue
		if profile.args[0] not in PROFILES:
			raise pytest.UsageError(f"{item.nodeid} names no profile of spec/harness/config.py: {profile.args[0]}")
		if not backend.IN_PROCESS:
			item.add_marker(pytest.mark.xdist_group(f"profile-{profile.args[0]}"))


def pytest_deselected(items):
	_run["deselected"] += len(items)


def pytest_collection_finish(session):
	_run["complete"] = not session.config.getoption("collectonly") and coverage.collected_whole_spec({item.path for item in session.items}, _run["deselected"], session.config.args)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
	if not item.path.is_relative_to(coverage.SPEC):
		return (yield)
	run_record.start(item.path, check_pages=_run["complete"])
	try:
		return (yield)
	finally:
		run_record.stop()


@pytest.hookimpl(optionalhook=True)
def pytest_testnodedown(node, error):
	output = getattr(node, "workeroutput", {}).get("spec_run")
	if output is None:
		_run["complete"] = False
		return
	_run["complete"] &= output["complete"]
	_run["seen"] |= {tuple(pair) for pair in output["seen"]}
	_run["pages"].append(output["pages"])


def pytest_sessionfinish(session, exitstatus):
	if hasattr(session.config, "workeroutput"):
		session.config.workeroutput["spec_run"] = {"complete": _run["complete"], "seen": sorted(coverage.seen()), "pages": pages.output()}
		return
	if exitstatus != pytest.ExitCode.OK or not _run["complete"]:
		return
	_run["unrequested"] = coverage.unrequested(_run["seen"] | coverage.seen())
	_run["page_problems"] = pages.problems([*_run["pages"], pages.output()])
	if _run["unrequested"] or _run["page_problems"]:
		session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_terminal_summary(terminalreporter):
	if _run["unrequested"]:
		terminalreporter.section("routes no spec test gets past the gate of", red=True)
		for route in _run["unrequested"]:
			terminalreporter.write_line(route)
		terminalreporter.write_line("(the run fails: every route needs a spec test outside spec/routes/ and spec/limits/ that the gate lets through)", red=True)
	for heading, problems in _run["page_problems"].items():
		terminalreporter.section(heading, red=True)
		for problem in problems:
			terminalreporter.write_line(problem)
		terminalreporter.write_line("(the run fails: pages must be readable, and may lead only to routes or to what the site serves beside the spec)", red=True)
