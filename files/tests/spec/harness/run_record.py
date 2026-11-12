'''
What the harness sees of a spec run, for the checks a run of the whole spec tier makes (coverage.py, pages.py): every exchange of a spec test's own clients, while the test itself runs, not its fixtures. The runner turns it on and off around each test (start, stop).
'''
from pathlib import Path

from files.tests.spec.harness import coverage, pages
from files.tests.spec.harness.routes import match

_test: Path | None = None
_pages = False
# Further checks of each exchange, (method, target, the row match() gave), that an implementation's own runner adds
_observers: list = []


def start(test_path: Path, *, check_pages: bool):
	'''Records the exchanges of the test in `test_path`, and with `check_pages`, checks where its pages lead (a run of the whole spec tier does).'''
	global _test, _pages
	_test, _pages = test_path, check_pages


def stop():
	global _test
	_test = None


def observe(observer):
	_observers.append(observer)


def exchange(method: str, target: str, response, *, api_client: bool, script_request: bool):
	'''Called by the client after each exchange.'''
	if _test is None:
		return
	matched = match(method, target)
	coverage.see(_test, method, matched, response)
	if _pages and not api_client and method in ("GET", "POST") and response.status == 200 and (response.header("Content-Type") or "").startswith("text/html"):
		pages.see(f"{matched.route.method} {matched.route.path}" if matched else f"{method} {target}", target, response.body, fragment=script_request)
	for observer in _observers:
		observer(method, target, matched)
