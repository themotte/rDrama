'''
A temporary ban that has run out ends on the banned user's next request to any page, through the browser or the API: their ban (and the mark of ban evasion that came with it) is cleared and they are told they've been unbanned, once. A ban that hasn't run out, and a permanent one, stay.
'''
import time

import pytest

from files.tests.spec.harness import *

PATHS = ["/", "/settings/profile", "/@{name}/info", "/admin"]


def _banned(until, **overrides):
	return factories.user(is_banned=seed.AUTOJANNY_ID, ban_reason="spam", unban_utc=until, **overrides)


def _client(how, user):
	return as_api(factories.api_token(user)) if how == "api" else as_user(user)


def _expect_unbanned(d, user):
	d.assert_exactly(
		updated={"users": {user["id"]: {"is_banned": 0, "unban_utc": 0, "ban_evade": 0}}},
		inserted={
			"comments": [{"author_id": seed.SYSTEM_ID, "parent_submission": None}],
			"notifications": [{"user_id": user["id"]}],
		},
	)


@pytest.mark.parametrize("path", PATHS)
def test_an_expired_ban_ends_on_the_next_request(path):
	user = _banned(int(time.time()) - 60, ban_evade=1, admin_level=2 if path == "/admin" else 0)
	client = _client("browser", user)

	with db_diff() as d:
		r = client.get(path.format(name=user["username"]))

	assert_status(r, 200)
	_expect_unbanned(d, user)


def test_an_expired_ban_ends_on_the_next_api_request():
	user = _banned(int(time.time()) - 60, ban_evade=1)
	client = _client("api", user)

	with db_diff() as d:
		r = client.get(f"/@{user['username']}/info")

	assert_status(r, 200)
	_expect_unbanned(d, user)


def test_the_user_is_told_once():
	user = _banned(int(time.time()) - 60)
	client = as_user(user)
	client.get("/settings/profile")

	with db_diff() as d:
		client.get("/settings/profile")

	d.assert_exactly()


@pytest.mark.parametrize("until", ["running", "permanent"])
def test_other_bans_stay(until):
	user = _banned(int(time.time()) + 3600 if until == "running" else 0)
	client = as_user(user)

	with db_diff() as d:
		r = client.get("/settings/profile")

	assert_status(r, 200)
	d.assert_exactly()
