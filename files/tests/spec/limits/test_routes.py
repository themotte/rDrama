'''
Each route's limits (harness/limits.py): its shortest limit serves as many requests as it allows in a window and refuses the next, and an exempt route refuses none, beyond the site-wide limits too.
'''
import pytest

from files.tests.spec.harness import *
from files.tests.spec.harness.limits import SITE_WIDE, assert_served_then_refused, limits_of, parse, paced, statuses_at
from files.tests.spec.harness.routes import ROUTES, fill

pytestmark = pytest.mark.profile("limits")

_CLIENT = {"X-Real-IP": "192.0.2.1"}


def _id(route) -> str:
	return f"{route.method} {route.path}"


@pytest.mark.parametrize("route", [r for r in ROUTES if limits_of(r)], ids=_id)
def test_a_routes_shortest_limit_serves_its_count(route):
	own = limits_of(route)
	count, period = own[0]
	offsets = paced(own + parse(SITE_WIDE), own[0], count + 1)
	client, path = anon(), fill(route)

	statuses = statuses_at(lambda: client.request(route.method, path, headers=_CLIENT), offsets)

	assert_served_then_refused(statuses, count)


@pytest.mark.parametrize("route", [r for r in ROUTES if not limits_of(r)], ids=_id)
def test_an_exempt_route_refuses_nothing(route):
	site_wide_count = parse(SITE_WIDE)[0][0]
	client, path = anon(), fill(route)

	statuses = statuses_at(lambda: client.request(route.method, path, headers=_CLIENT), [0] * (site_wide_count + 1))

	assert_served_then_refused(statuses, site_wide_count + 1)
