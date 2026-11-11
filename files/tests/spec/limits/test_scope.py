'''
What each route's limits count (harness/limits.py): each row of the route table apart, HEAD with GET, and not OPTIONS or requests no row answers.
'''
import pytest

from files.tests.spec.harness import *
from files.tests.spec.harness.limits import DEFAULT, OWN, SITE_WIDE, assert_served_then_refused, limits_of, parse, statuses_at
from files.tests.spec.harness.routes import ANYONE, PUBLIC, ROUTES, fill

pytestmark = pytest.mark.profile("limits")

_CLIENT = {"X-Real-IP": "192.0.2.1"}


def _request(client, method, path):
	return lambda: client.request(method, path, headers=_CLIENT)


def _first_limit(method, path):
	return limits_of(next(r for r in ROUTES if (r.method, r.path) == (method, path)))[0][0]


def test_the_get_and_post_rows_of_a_path_count_apart():
	path = "/tasks/scheduled_posts"
	assert _first_limit("GET", path) == _first_limit("POST", path)
	client = anon()
	statuses_at(_request(client, "POST", path), [0] * (_first_limit("POST", path) + 1))

	statuses = statuses_at(_request(client, "GET", path), [0] * (_first_limit("GET", path) + 1))

	assert_served_then_refused(statuses, _first_limit("GET", path))


def test_rows_alike_count_apart():
	assert OWN[("GET", "/")] == OWN[("GET", "/catalog")]
	client = anon()
	statuses_at(_request(client, "GET", "/"), [0] * (_first_limit("GET", "/") + 1))

	statuses = statuses_at(_request(client, "GET", "/catalog"), [0] * (_first_limit("GET", "/catalog") + 1))

	assert_served_then_refused(statuses, _first_limit("GET", "/catalog"))


def test_head_counts_toward_its_get_row():
	count = _first_limit("GET", "/")
	client = anon()
	statuses_at(_request(client, "HEAD", "/"), [0] * (count - 1))

	statuses = statuses_at(_request(client, "GET", "/"), [0, 0])

	assert_served_then_refused(statuses, 1)


def test_options_counts_toward_nothing_of_its_row():
	count = _first_limit("GET", "/")
	client = anon()
	statuses_at(_request(client, "OPTIONS", "/"), [0] * (count + 1))

	assert_served_then_refused(statuses_at(_request(client, "GET", "/"), [0] * (count + 1)), count)


@pytest.mark.parametrize(("method", "path"), [("OPTIONS", "/"), ("GET", "/no-route-answers-this"), ("PUT", "/"), ("GET", "/settings//blocks")], ids=["OPTIONS", "no such path", "no such method", "doubled slash"])
def test_requests_no_row_serves_count_toward_nothing(method, path):
	site_wide = parse(SITE_WIDE)[0][0]
	defaults = [r for r in ROUTES if r.access not in (PUBLIC, ANYONE) and (r.method, r.path) not in OWN and limits_of(r)][:4]
	assert parse(DEFAULT)[0][0] * len(defaults) > site_wide
	client = anon()
	statuses_at(_request(client, method, path), [0] * (site_wide + 5))

	statuses = [statuses_at(_request(client, r.method, fill(r)), [0])[0] for r in (defaults * site_wide)[:site_wide + 1]]

	assert_served_then_refused(statuses, site_wide)


@pytest.mark.parametrize("headers", [{"User-Agent": ""}, {"Host": "elsewhere.example"}], ids=["no User-Agent", "another site's Host"])
def test_requests_refused_before_the_limits_count_toward_nothing(headers):
	count = _first_limit("POST", "/login")
	client = anon()
	statuses_at(lambda: client.request("POST", "/login", headers={**_CLIENT, **headers}), [0] * (count + 5))

	assert_served_then_refused(statuses_at(_request(client, "POST", "/login"), [0] * (count + 1)), count)
