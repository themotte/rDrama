'''
POST /@<username>/revert_actions undoes what the named admin did in the last day (their removals, bans and shadowbans), logs the revert in the mod log against that admin, and answers a JSON message.
'''
from files.tests.spec.harness import *


def test_reverting_an_admin_without_recent_actions_only_logs_it():
	target = factories.admin(2)
	admin = factories.admin(3)

	with db_diff() as d:
		r = as_user(admin).post(f"/@{target['username']}/revert_actions")

	assert_json_message(r)
	d.assert_exactly(inserted={"modactions": [{"kind": "revert", "user_id": admin["id"], "target_user_id": target["id"], "target_submission_id": None, "target_comment_id": None}]})


def test_reverting_an_unknown_user_is_not_found():
	admin = factories.admin(3)
	username = factories.unique()

	with db_diff() as d:
		r = as_user(admin).post(f"/@{username}/revert_actions", headers=XHR)

	assert_status(r, 404)
	d.assert_exactly()
