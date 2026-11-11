'''The spec runs with the rate limits off, but for its tests in the "limits" profile (harness/limits.py).'''
from files.tests.spec.harness import *
from files.tests.spec.harness.limits import OWN, parse


def test_the_limits_are_off_outside_the_limits_profile():
	assert parse(OWN[("POST", "/login")])[0] == (1, 1)
	client = anon()

	statuses = [client.post_raw("/login", headers={"X-Real-IP": "192.0.2.1"}).status for _ in range(20)]

	assert 429 not in statuses and len(set(statuses)) == 1, statuses
