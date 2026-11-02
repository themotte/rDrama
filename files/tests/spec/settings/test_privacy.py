'''
POST /id/<user id>/private/<0|1>: private profiles.

Members may change only their own, and only once they meet the site's thresholds (site settings min_comments_private_profile, min_truescore_private_profile, min_age_days_private_profile). Admins of level 2 and up may change anyone's, regardless of thresholds.
'''
import time

import pytest

from files.tests.spec.harness import *

DAY = 86400


def _privacy_path(user, enabled):
	return f"/id/{user['id']}/private/{enabled}"


@pytest.mark.parametrize("enabled, stored", [(1, True), (0, False)])
def test_users_can_set_their_own_profile_privacy(enabled, stored):
	u = factories.user(is_private=not stored)

	with db_diff() as d:
		r = as_user(u).post(_privacy_path(u, enabled))

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {"is_private": stored}}})


def test_requires_login():
	u = factories.user()

	assert_api_unauthorized(anon().post_raw(_privacy_path(u, 1), headers=XHR))


def test_privacy_value_must_be_0_or_1():
	u = factories.user()

	assert_status(as_user(u).post(_privacy_path(u, 2), headers=XHR), 400)


def test_privacy_of_an_unknown_user_is_not_found():
	u = factories.user()
	gone = factories.user()
	db.delete("users", id=gone["id"])

	assert_status(as_user(u).post(_privacy_path(gone, 1), headers=XHR), 404)


def test_members_cannot_set_others_privacy():
	target = factories.user()
	member = as_user(factories.admin(level=1))

	with db_diff() as d:
		r = member.post(_privacy_path(target, 1), headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


def test_admins_can_set_others_privacy():
	target = factories.user()
	admin = as_user(factories.admin(level=2))

	with db_diff() as d:
		r = admin.post(_privacy_path(target, 1))

	assert_json_message(r)
	d.assert_exactly(updated={"users": {target["id"]: {"is_private": True}}})


@pytest.mark.parametrize("setting, short, enough", [
	("min_comments_private_profile", {"comment_count": 4}, {"comment_count": 5}),
	("min_truescore_private_profile", {"truescore": 4}, {"truescore": 5}),
	("min_age_days_private_profile", {"created_utc": int(time.time()) - int(4.5 * DAY)}, {"created_utc": int(time.time()) - int(5.5 * DAY)}),
])
def test_going_private_requires_meeting_each_site_threshold(setting, short, enough):
	site_settings_set(setting, 5)
	newcomer = factories.user(**short)
	veteran = factories.user(**enough)

	assert_status(as_user(newcomer).post(_privacy_path(newcomer, 1), headers=XHR), 403)
	assert_json_message(as_user(veteran).post(_privacy_path(veteran, 1)))


def test_admins_bypass_thresholds_for_their_own_profile():
	site_settings_set("min_comments_private_profile", 5)
	admin = factories.admin(level=2, comment_count=0)

	assert_json_message(as_user(admin).post(_privacy_path(admin, 1)))
