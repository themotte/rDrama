'''
Route coverage: a run of the whole spec tier must get past the gate of every route in the spec's route table (routes.py) from some spec test outside spec/routes/ and spec/limits/, whose generic cells say nothing of what a route does. A request counts when its path names the row as written (routes.match: not merely redirected there; HEAD and OPTIONS don't count) and the route answered it past its gate: with neither 401, 403, a login redirect nor 404 or 405 (which an implementation without the route would answer, so they show nothing of it). Requests count from the test itself, not its fixtures (run_record).
'''
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1]
_GENERIC_CELLS = (SPEC / "routes", SPEC / "limits")

_seen: set[tuple[str, str]] = set()


def counts(test_path: Path) -> bool:
	'''Whether the requests of the test in `test_path` count.'''
	return test_path.is_relative_to(SPEC) and not any(test_path.is_relative_to(cells) for cells in _GENERIC_CELLS)


def see(test_path: Path, method: str, matched, response):
	if matched is None or matched.redirected or method in ("HEAD", "OPTIONS") or not counts(test_path):
		return
	location = (response.header("Location") or "").split("?")[0]
	if response.status in (401, 403, 404, 405) or (response.status == 302 and location.endswith("/login")):
		return
	_seen.add((matched.route.method, matched.route.path))


def seen() -> set[tuple[str, str]]:
	return set(_seen)


def collected_whole_spec(item_paths: set[Path], deselected: int, args: list[str]) -> bool:
	'''Whether a process's collection holds every spec test.'''
	return deselected == 0 and not any("::" in a for a in args) and set(SPEC.rglob("test_*.py")) <= item_paths


def unrequested(seen: set[tuple[str, str]]) -> list[str]:
	from files.tests.spec.harness.routes import ROUTES
	return [f"{r.method} {r.path}" for r in ROUTES if (r.method, r.path) not in seen]
