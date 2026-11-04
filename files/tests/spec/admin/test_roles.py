'''
Granting and revoking admin rights, both for level-3 admins only and answering JSON:
- POST /@<username>/make_admin makes the user a level-2 admin.
- POST /@<username>/remove_admin takes all admin rights away (level 0).

Both log a mod action naming the target, and do nothing (still answering success) when the user is already at that level. Neither touches a level-3 admin or a system account (403): those change only in the database. An unknown username is 404.
'''
import pytest

from files.tests.spec.harness import *


@pytest.mark.parametrize("level", [0, 1])
def test_make_admin_raises_the_user_to_level_2(level):
	admin = factories.admin(3)
	target = factories.admin(level)
	client = as_user(admin)

	with db_diff() as d:
		r = client.post(f"/@{target['username']}/make_admin")

	assert_json_message(r)
	d.assert_exactly(
		updated={"users": {target["id"]: {"admin_level": 2}}},
		inserted={"modactions": [{"kind": "make_admin", "user_id": admin["id"], "target_user_id": target["id"], "target_submission_id": None, "target_comment_id": None}]},
	)


@pytest.mark.parametrize("level", [1, 2])
def test_remove_admin_lowers_the_user_to_level_0(level):
	admin = factories.admin(3)
	target = factories.admin(level)
	client = as_user(admin)

	with db_diff() as d:
		r = client.post(f"/@{target['username']}/remove_admin")

	assert_json_message(r)
	d.assert_exactly(
		updated={"users": {target["id"]: {"admin_level": 0}}},
		inserted={"modactions": [{"kind": "remove_admin", "user_id": admin["id"], "target_user_id": target["id"], "target_submission_id": None, "target_comment_id": None}]},
	)


@pytest.mark.parametrize("action, level", [("make_admin", 2), ("remove_admin", 0)])
def test_granting_or_revoking_admin_to_the_level_already_held_changes_nothing(action, level):
	target = factories.admin(level)
	client = as_user(factories.admin(3))

	with db_diff() as d:
		r = client.post(f"/@{target['username']}/{action}")

	assert_json_message(r)
	d.assert_exactly()


@pytest.mark.parametrize("action", ["make_admin", "remove_admin"])
def test_level_3_admins_are_left_alone(action):
	admin = factories.admin(3)
	target = factories.admin(3)

	with db_diff() as d:
		r = as_user(admin).post(f"/@{target['username']}/{action}", headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("action", ["make_admin", "remove_admin"])
def test_system_accounts_are_left_alone(action):
	client = as_user(factories.admin(3))

	with db_diff() as d:
		r = client.post(f"/@AutoJanny/{action}", headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("action", ["make_admin", "remove_admin"])
def test_granting_or_revoking_admin_for_an_unknown_user_is_not_found(action):
	client = as_user(factories.admin(3))

	with db_diff() as d:
		r = client.post(f"/@{factories.unique('nobody')}/{action}", headers=XHR)

	assert_status(r, 404)
	d.assert_exactly()
