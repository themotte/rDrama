'''
What the harness sees of a spec run, for the checks a run of the whole spec tier makes (coverage.py): every exchange of a spec test's own clients, while the test itself runs, not its fixtures. The runner turns it on and off around each test (start, stop).
'''
from pathlib import Path

from files.tests.spec.harness import coverage
from files.tests.spec.harness.routes import match

_test: Path | None = None
# Further checks of each exchange, (method, target, the row match() gave), that an implementation's own runner adds
_observers: list = []


def start(test_path: Path):
	global _test
	_test = test_path


def stop():
	global _test
	_test = None


def observe(observer):
	_observers.append(observer)


def exchange(method: str, target: str, response):
	'''Called by the client after each exchange.'''
	if _test is None:
		return
	matched = match(method, target)
	coverage.see(_test, method, matched, response)
	for observer in _observers:
		observer(method, target, matched)
