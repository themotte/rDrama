'''
Whom limits count for (harness/limits.py): the client's address, from its X-Real-IP header or else its connection's peer, logged in or not; and a crawler's limits for its User-Agent, whatever the address.
'''
import pytest

from files.tests.spec.harness import *
from files.tests.spec.harness import http
from files.tests.spec.harness.limits import CRAWLERS, EXEMPT, OWN, assert_served_then_refused, limits_of, parse, statuses_at
from files.tests.spec.harness.routes import ROUTES, USER, fill

pytestmark = pytest.mark.profile("limits")

_ROUTE = ("POST", "/login")
_COUNT = limits_of(next(r for r in ROUTES if (r.method, r.path) == _ROUTE))[0][0]


def _fill(client, headers=None):
	'''Sends the route the requests its shortest limit serves, and one more; the statuses.'''
	return statuses_at(lambda: client.request(*_ROUTE, headers=headers), [0] * (_COUNT + 1))


def test_clients_with_different_real_ips_count_apart():
	_fill(anon(), {"X-Real-IP": "192.0.2.1"})

	assert_served_then_refused(_fill(anon(), {"X-Real-IP": "192.0.2.2"}), _COUNT)


def test_without_a_real_ip_clients_count_by_the_address_they_connect_from():
	_fill(anon(peer="127.0.0.2"))

	assert_served_then_refused(_fill(anon(peer="127.0.0.3")), _COUNT)


def test_clients_connecting_from_one_address_without_a_real_ip_count_together():
	_fill(anon(peer="127.0.0.2"))

	assert _fill(anon(peer="127.0.0.2")) == [429] * (_COUNT + 1)


def test_clients_sharing_a_real_ip_count_together_whatever_their_address():
	_fill(anon(peer="127.0.0.2"), {"X-Real-IP": "192.0.2.1"})

	assert _fill(anon(peer="127.0.0.3"), {"X-Real-IP": "192.0.2.1"}) == [429] * (_COUNT + 1)


def test_a_real_ip_counts_without_the_spaces_around_it():
	_fill(anon(), {"X-Real-IP": " 192.0.2.1 "})

	assert _fill(anon(), {"X-Real-IP": "192.0.2.1"}) == [429] * (_COUNT + 1)


def test_a_blank_real_ip_counts_as_none():
	_fill(anon(peer="127.0.0.2"), {"X-Real-IP": " "})

	assert _fill(anon(peer="127.0.0.2")) == [429] * (_COUNT + 1)


def test_a_member_counts_by_address_too():
	route = next(r for r in ROUTES if r.method == "GET" and r.access == USER and limits_of(r) and (r.method, r.path) not in OWN and "<" not in r.path)
	count = limits_of(route)[0][0]
	member = as_user(factories.user())
	statuses_at(lambda: member.get(route.path, headers={"X-Real-IP": "192.0.2.1"}), [0] * (count + 1))

	statuses = statuses_at(lambda: member.get(route.path, headers={"X-Real-IP": "192.0.2.2"}), [0] * (count + 1))

	assert_served_then_refused(statuses, count)


# Exempt rows, which count nothing else
_EXEMPT_ROUTES = [r for r in ROUTES if (r.method, r.path) in EXEMPT and r.method == "GET"][:2]
_CRAWLER = "Mozilla/5.0 (compatible; ExampleBot/1.0)"
_CRAWLER_COUNT = parse(CRAWLERS)[0][0]


def _from_many_addresses(route, user_agent, requests):
	client, path = anon(), fill(route)
	addresses = iter(range(1, requests + 1))
	return statuses_at(lambda: client.get(path, headers={"User-Agent": user_agent, "X-Real-IP": f"198.51.100.{next(addresses)}"}), [0] * requests)


@pytest.mark.parametrize("user_agent", [_CRAWLER, "Mozilla/5.0 (compatible; Bytespider; spider-feedback@bytedance.com)", "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ChatGPT-User/1.0", "CUBOT NOTE 30"], ids=["bot", "bytespider", "chatgpt-user", "bot within a word"])
def test_a_crawlers_limit_counts_its_user_agent_from_any_address(user_agent):
	assert_served_then_refused(_from_many_addresses(_EXEMPT_ROUTES[0], user_agent, _CRAWLER_COUNT + 1), _CRAWLER_COUNT)


def test_a_crawlers_limit_counts_each_route_apart():
	_from_many_addresses(_EXEMPT_ROUTES[0], _CRAWLER, _CRAWLER_COUNT + 1)

	assert_served_then_refused(_from_many_addresses(_EXEMPT_ROUTES[1], _CRAWLER, _CRAWLER_COUNT + 1), _CRAWLER_COUNT)


def test_another_crawlers_user_agent_counts_apart():
	_from_many_addresses(_EXEMPT_ROUTES[0], _CRAWLER, _CRAWLER_COUNT + 1)

	assert_served_then_refused(_from_many_addresses(_EXEMPT_ROUTES[0], "Mozilla/5.0 (compatible; OtherBot/2.0)", _CRAWLER_COUNT + 1), _CRAWLER_COUNT)


def test_a_crawlers_user_agent_counts_as_sent():
	_from_many_addresses(_EXEMPT_ROUTES[0], _CRAWLER, _CRAWLER_COUNT + 1)

	assert_served_then_refused(_from_many_addresses(_EXEMPT_ROUTES[0], _CRAWLER.upper(), _CRAWLER_COUNT + 1), _CRAWLER_COUNT)


def test_a_browsers_user_agent_isnt_a_crawlers():
	statuses = _from_many_addresses(_EXEMPT_ROUTES[0], http.DEFAULT_USER_AGENT, _CRAWLER_COUNT + 1)

	assert_served_then_refused(statuses, _CRAWLER_COUNT + 1)
