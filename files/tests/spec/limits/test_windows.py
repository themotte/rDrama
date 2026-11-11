'''
How limits count (harness/limits.py): each distinct limit serves its count in a window, windows aligned to the epoch, refused requests counting toward nothing, and the site-wide limits across a client's routes.
'''
import pytest

from files.tests.spec.harness import *
from files.tests.spec.harness.limits import DEFAULT, EXEMPT, OWN, SITE_WIDE, assert_served_then_refused, limits_of, most_in_a_window, parse, paced, statuses_at
from files.tests.spec.harness.routes import ANYONE, PUBLIC, ROUTES, fill

pytestmark = pytest.mark.profile("limits")

_CLIENT = {"X-Real-IP": "192.0.2.1"}
# Larger ones would take too many requests to fill
_LARGEST_TESTED = 250
_GATED = [r for r in ROUTES if r.access not in (PUBLIC, ANYONE) and limits_of(r)]


def _row(method, path):
	return next(r for r in ROUTES if (r.method, r.path) == (method, path))


def _send(route, client=None):
	client, path = client or anon(), fill(route)
	return lambda: client.request(route.method, path, headers=_CLIENT)


def _distinct_limits():
	'''Each distinct limit of up to _LARGEST_TESTED a window, with a row having it: one its gate refuses an anonymous client, where there is one, for a cheap answer.'''
	rows = {}
	for route in sorted(ROUTES, key=lambda r: r in _GATED, reverse=True):
		for limit in limits_of(route):
			if limit[0] <= _LARGEST_TESTED:
				rows.setdefault(limit, route)
	return [pytest.param(limit, route, id=f"{limit[0]} per {limit[1]}s") for limit, route in sorted(rows.items())]


@pytest.mark.parametrize(("limit", "route"), _distinct_limits())
def test_a_limit_serves_its_count_in_its_window(limit, route):
	offsets = paced(limits_of(route) + parse(SITE_WIDE), limit, limit[0] + 1)

	statuses = statuses_at(_send(route), offsets)

	assert_served_then_refused(statuses, limit[0])


def test_a_window_ends_on_the_period_after_it_starts():
	route = _row("POST", "/submit")

	statuses = statuses_at(_send(route), [0, 0.999, 1])

	assert statuses[1:] == [429, statuses[0]] and statuses[0] != 429


def test_windows_are_aligned_to_the_epoch_not_to_a_clients_first_request():
	route = _row("POST", "/submit")

	statuses = statuses_at(_send(route), [0.9, 0.95, 1.0])

	assert statuses[1:] == [429, statuses[0]] and statuses[0] != 429


def test_longer_windows_are_aligned_to_the_epoch_too():
	route = _row("POST", "/submit")
	assert parse(OWN[("POST", "/submit")])[:2] == [(1, 1), (2, 60)]

	statuses = statuses_at(_send(route), [50, 55, 58, 60])

	assert statuses[2:] == [429, statuses[0]] and statuses[:2] == [statuses[0]] * 2 and statuses[0] != 429


def test_refused_requests_count_toward_no_limit():
	route = _row("POST", "/submit")
	assert parse(OWN[("POST", "/submit")])[:2] == [(1, 1), (2, 60)]

	statuses = statuses_at(_send(route), [0] * 6 + [1, 2])

	assert_served_then_refused(statuses[:6], 1)
	assert statuses[6:] == [statuses[0], 429]


def test_the_site_wide_limits_count_a_clients_requests_to_every_route():
	defaults = [r for r in _GATED if (r.method, r.path) not in OWN][:8]
	count, period = parse(SITE_WIDE)[1]
	assert period == 60
	spacing = 0.25
	offsets = [i * spacing for i in range(count + 1)]
	per_row = [offsets[i::len(defaults)] for i in range(len(defaults))]
	assert all(most_in_a_window(times, p) <= c for times in per_row for c, p in parse(DEFAULT)), "a row's own limit would bind first"
	assert most_in_a_window(offsets, 1) <= parse(SITE_WIDE)[0][0]
	client = anon()

	statuses = []
	for i, offset in enumerate(offsets):
		statuses += statuses_at(_send(defaults[i % len(defaults)], client), [offset])

	assert_served_then_refused(statuses, count)


def test_exempt_routes_count_toward_no_site_wide_limit():
	exempt = next(r for r in ROUTES if (r.method, r.path) in EXEMPT)
	defaults = [r for r in _GATED if (r.method, r.path) not in OWN][:4]
	count = parse(SITE_WIDE)[0][0]
	client = anon()

	statuses_at(_send(exempt, client), [0] * (count + 5))
	statuses = [statuses_at(_send(defaults[i % len(defaults)], client), [0])[0] for i in range(count + 1)]

	assert_served_then_refused(statuses, count)
