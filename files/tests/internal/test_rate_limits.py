'''The site's rate limiter (files/helpers/rate_limits.py): its windows and counting, and its key.'''
import os
import subprocess

import flask
import pytest
import redis
from flask import request
from werkzeug.exceptions import TooManyRequests

import files.__main__ as main
from files.__main__ import app
from files.helpers.config.environment import CACHE_REDIS_URL
from files.helpers.rate_limits import _COUNTER_GRACE, Limit, RateLimiter, client_address, parse
from files.tests.spec.harness import anon, backend_inprocess
from files.tests.testenv import REPO_ROOT


@pytest.mark.parametrize(("headers", "peer", "address"), [
	({"X-Real-IP": "192.0.2.1"}, "127.0.0.1", "192.0.2.1"),
	({"X-Real-IP": " 192.0.2.1 "}, "127.0.0.1", "192.0.2.1"),
	({}, "198.51.100.7", "198.51.100.7"),
	({"X-Real-IP": ""}, "198.51.100.7", "198.51.100.7"),
	({"X-Real-IP": "  "}, "198.51.100.7", "198.51.100.7"),
], ids=["header", "header with spaces", "peer", "blank header", "spaces only"])
def test_the_client_is_the_real_ip_header_or_else_the_peer(headers, peer, address):
	with app.test_request_context(headers=headers, environ_base={"REMOTE_ADDR": peer}):
		assert client_address() == address


T0 = 1924992000.0  # 2031-01-01T00:00:00Z, the start of a window of every period


@pytest.fixture
def clock(monkeypatch):
	'''Turns the site's limiter on, on a clock the test sets.'''
	now = [T0]
	monkeypatch.setattr(main.limiter, "enabled", True)
	monkeypatch.setattr(main.limiter, "clock", lambda: now[0])
	return now


def _served(text, scope="probe", limiter=None):
	with app.test_request_context(headers={"X-Real-IP": "192.0.2.1"}):
		try:
			(limiter or main.limiter).check_now(scope, text)
		except TooManyRequests:
			return False
	return True


def test_limits_are_parsed():
	assert parse("1/second;30/minute;200/hour;1000/day") == (Limit(1, 1), Limit(30, 60), Limit(200, 3600), Limit(1000, 86400))


def test_a_limit_serves_its_count_in_a_window(clock):
	assert [_served("3/second") for _ in range(4)] == [True, True, True, False]


def test_windows_are_aligned_to_the_epoch(clock):
	clock[0] = T0 + 0.9
	assert [_served("1/second") for _ in range(2)] == [True, False]
	clock[0] = T0 + 0.999
	assert not _served("1/second")
	clock[0] = T0 + 1
	assert _served("1/second")


def test_refused_requests_count_toward_no_limit(clock):
	served = []
	for second in range(4):
		clock[0] = T0 + second
		served += [_served("1/second;3/minute") for _ in range(3)]

	assert served == [True, False, False] * 3 + [False] * 3


def test_scopes_count_apart(clock):
	assert [_served("1/second", "a"), _served("1/second", "b"), _served("1/second", "a")] == [True, True, False]


def test_a_counter_lasts_beyond_its_window(clock):
	_served("1/minute")

	[key] = _redis().keys("ratelimit:*")
	assert 60 < _redis().ttl(key) <= 60 + _COUNTER_GRACE


def test_nothing_is_counted_while_the_limiter_is_off(clock):
	main.limiter.enabled = False

	assert all(_served("1/second") for _ in range(3))
	assert _redis().keys("ratelimit:*") == []


def test_an_unreachable_store_fails_the_request_rather_than_refusing_it(clock):
	unreachable = RateLimiter("redis://127.0.0.1:1/0", default="1/second", site_wide="1/second", crawlers="1/second", is_crawler=lambda: False, enabled=True)

	with pytest.raises(redis.ConnectionError):
		_served("1/second", limiter=unreachable)


def _redis():
	return redis.Redis.from_url(CACHE_REDIS_URL)


def test_the_site_counts_its_requests(clock):
	client = anon()

	assert [client.get("/robots.txt").status for _ in range(4)] == [200, 200, 200, 429]


@pytest.mark.parametrize(("variables", "enabled"), [
	({}, True),
	({"DBG_LIMITER_DISABLED": "true"}, False),
	({"SPEC_TEST_MODE": "1"}, False),
	({"SPEC_TEST_MODE": "1", "SPEC_TEST_LIMITS": "1"}, True),
	({"SPEC_TEST_MODE": "1", "SPEC_TEST_LIMITS": "1", "DBG_LIMITER_DISABLED": "true"}, True),
], ids=["production", "developer's switch", "test mode", "test mode with limits", "test mode with limits, developer's switch set"])
def test_the_limiter_is_on_in_production_and_where_test_mode_says(variables, enabled):
	env = {name: value for name, value in os.environ.items() if name not in ("SPEC_TEST_MODE", "SPEC_TEST_LIMITS", "DBG_LIMITER_DISABLED")}
	result = subprocess.run(["python3", "-c", "from files.__main__ import limiter; print(limiter.enabled)"], cwd=REPO_ROOT, env={**env, **variables}, capture_output=True, text=True)

	assert result.returncode == 0, result.stderr
	assert result.stdout.strip() == str(enabled)


def test_the_limits_profile_turns_the_limiter_on_for_its_tests():
	backend_inprocess.reset("limits")
	assert main.limiter.enabled

	backend_inprocess.reset(None)
	assert not main.limiter.enabled


def test_a_clients_peer_is_the_address_it_connects_from():
	peers = []
	def record(sender, **extra):
		peers.append(request.remote_addr)
	flask.request_started.connect(record, app)
	try:
		anon(peer="127.0.0.2").get("/robots.txt")
		anon().get("/robots.txt")
	finally:
		flask.request_started.disconnect(record, app)

	assert peers == ["127.0.0.2", "127.0.0.1"]
