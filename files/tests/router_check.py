'''
A check of the harness's route matching (spec/harness/routes.py match) on the run's own traffic: in-process, every request a spec test makes must reach the row by the app's router that the harness says it reaches, or the run fails. Route coverage itself is the harness's (spec/harness/coverage.py).
'''
from files.tests.spec.harness import run_record

# The row the router reached for the latest request
_router_row: str | None = None
_mismatches: set[str] = set()
_connected = False


def _record(sender, response, **extra):
	global _router_row
	from flask import request
	from files.tests import route_table
	rule = request.url_rule
	_router_row = None if rule is None or rule.rule.startswith(route_table._UNSPECIFIED_PREFIXES) else f"{'GET' if request.method == 'HEAD' else request.method} {route_table.path_of(rule.rule)}"


_NOTHING = "no request reaching the router"


def _compare(method, target, matched):
	global _router_row
	if method != "OPTIONS":
		harness = None if matched is None or matched.redirected else f"{matched.route.method} {matched.route.path}"
		if harness != _router_row:
			_mismatches.add(f"{method} {target}: the router reached {_router_row}, the harness {harness}")
	_router_row = _NOTHING


def connect():
	global _connected
	if _connected:
		return
	import flask
	from files.__main__ import app
	flask.request_finished.connect(_record, app)
	run_record.observe(_compare)
	_connected = True


def mismatches() -> set[str]:
	return set(_mismatches)
