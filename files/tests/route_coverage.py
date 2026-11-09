'''
Route coverage: a run of the whole spec tier must get past the gate of every route in the spec's route table (harness/routes.py) from some spec test outside spec/routes/, whose generic cells say nothing of what a route does. A request counts when the gate let it through: it was answered with neither 401, 403 nor a login redirect. Requests count from the test itself, not its fixtures.
'''
from pathlib import Path

from files.tests import testenv

SPEC = testenv.REPO_ROOT / "files" / "tests" / "spec"
_GENERIC_CELLS = SPEC / "routes"

_seen: set[tuple[str, str]] = set()
_recording = False
_connected = False


def _record(sender, response, **extra):
	from flask import request
	from files.tests import route_table
	if not _recording or request.url_rule is None or request.method in ("HEAD", "OPTIONS"): return
	if response.status_code in (401, 403) or (response.status_code == 302 and (response.location or "").split("?")[0].endswith("/login")): return
	_seen.add((request.method, route_table.path_of(request.url_rule.rule)))


def start(path: Path):
	'''Records the requests of a test in `path`, if it is one that counts.'''
	global _recording, _connected
	if not _connected:
		import flask
		from files.__main__ import app
		flask.request_finished.connect(_record, app)
		_connected = True
	_recording = path.is_relative_to(SPEC) and not path.is_relative_to(_GENERIC_CELLS)


def stop():
	global _recording
	_recording = False


def seen() -> set[tuple[str, str]]:
	return set(_seen)


def collected_whole_spec(item_paths: set[Path], deselected: int, args: list[str]) -> bool:
	'''Whether a process's collection holds every spec test.'''
	return deselected == 0 and not any("::" in a for a in args) and set(SPEC.rglob("test_*.py")) <= item_paths


def unrequested(seen: set[tuple[str, str]]) -> list[str]:
	from files.tests.spec.harness.routes import ROUTES
	return [f"{r.method} {r.path}" for r in ROUTES if (r.method, r.path) not in seen]
