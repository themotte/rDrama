'''
The spec's route table (files/tests/spec/harness/routes.py) lists exactly the application's routes, with the gates their decorators give them and the API-client refusals their views make directly. Gates a view applies in other ways are for the spec files of its area; this only keeps the table from drifting from the code.
'''
import pytest

from files.__main__ import app
from files.tests import route_table
from files.tests.spec.harness.routes import ROUTES

_APP_ROUTES = route_table.app_routes(app)


def test_the_table_lists_each_route_once():
	pairs = [(r.method, r.path) for r in ROUTES]
	assert len(pairs) == len(set(pairs)), sorted(p for p in pairs if pairs.count(p) > 1)


def test_the_table_lists_exactly_the_applications_routes():
	listed = {(r.method, r.path) for r in ROUTES}
	assert listed == set(_APP_ROUTES), {"unlisted": sorted(set(_APP_ROUTES) - listed), "not routes": sorted(listed - set(_APP_ROUTES))}


@pytest.mark.parametrize("route", [r for r in ROUTES if (r.method, r.path) in _APP_ROUTES], ids=lambda r: f"{r.method} {r.path}")
def test_each_routes_gates_are_its_views(route):
	assert (route.access, route.api_clients) == route_table.gates_of(_APP_ROUTES[(route.method, route.path)])


def test_the_table_is_sorted():
	assert ROUTES == sorted(ROUTES, key=lambda r: (r.path, r.method))
