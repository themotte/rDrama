'''
GET /banned, open to everyone, lists the permanently suspended accounts, each with the reason given (as text: what the admin typed reads as typed) and a link to the admin who suspended them. Temporarily suspended accounts aren't listed.
'''
import time

import pytest

from files.tests.spec.harness import *


def _suspended(**overrides):
	admin = factories.admin(2)
	return factories.user(is_banned=admin["id"], ban_reason=factories.unique("reason"), **overrides), admin


@pytest.mark.parametrize("client", [anon, lambda: as_user(factories.user())], ids=["visitor", "user"])
def test_permanent_suspensions_are_listed_with_reason_and_admin(client):
	user, admin = _suspended(unban_utc=0)

	r = client().get("/banned")

	assert_html(r, 200)
	for token in (user["username"], user["ban_reason"], admin["username"]):
		assert_in_payload(r, token)


def test_temporary_suspensions_and_others_arent_listed():
	temporary, _ = _suspended(unban_utc=int(time.time()) + 86400)
	unsuspended = factories.user()

	r = anon().get("/banned")

	assert_not_in_payload(r, temporary["username"])
	assert_not_in_payload(r, unsuspended["username"])


def test_the_reason_reads_as_the_admin_typed_it():
	user, admin = factories.user(), factories.admin(2)
	token = factories.unique("reason")
	as_user(admin).post(f"/ban_user/{user['id']}", {"reason": f"{token} don't & <b>"})

	r = anon().get("/banned")

	assert f"{token} don't & <b>" in element_text(r, f"banned-{user['id']}")


def test_the_admin_who_suspended_is_linked():
	user, admin = _suspended(unban_utc=0)

	assert_in_payload(anon().get("/banned"), f'href="/@{admin["username"]}"')
