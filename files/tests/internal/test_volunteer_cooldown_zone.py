'''
The volunteer cooldown (spec/volunteer/test_duty.py) is kept in UTC whatever the server's local time zone: users.volunteer_last_started_utc holds UTC and is compared with UTC. The spec's processes run in UTC, so this runs the site in another zone.
'''
import os
import time

import pytest

from files.tests.spec.harness import *


@pytest.fixture(autouse=True)
def new_york():
	before = os.environ.get("TZ")
	os.environ["TZ"] = "America/New_York"
	time.tzset()
	yield
	if before is None:
		del os.environ["TZ"]
	else:
		os.environ["TZ"] = before
	time.tzset()


def _eligible():
	comment = factories.comment(factories.user(), factories.post(factories.user()), state_report="REPORTED")
	factories.report(factories.user(), comment)
	return comment


def test_a_volunteer_who_started_21_hours_ago_gets_a_duty():
	comment = _eligible()
	volunteer = factories.user()
	db.execute("UPDATE users SET volunteer_last_started_utc = timezone('UTC', now()) - interval '21 hours' WHERE id = :id", id=volunteer["id"])

	r = as_user(volunteer).get("/volunteer")

	assert_html(r, 200)
	assert_in_payload(r, comment["body"])


def test_the_start_is_stored_in_utc():
	_eligible()
	volunteer = factories.user()

	as_user(volunteer).get("/volunteer")

	assert db.execute("SELECT abs(extract(epoch FROM timezone('UTC', now()) - volunteer_last_started_utc)) < 60 FROM users WHERE id = :id", id=volunteer["id"])
