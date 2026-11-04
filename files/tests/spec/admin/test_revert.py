'''
POST /@<username>/revert_actions undoes what the named admin did in the last day, logs the revert in the mod log against that admin, and answers a JSON message. Posts and comments they removed that are still removed come back as approving them would (ones held for approval since stay held); users they banned or shadowbanned are unbanned, and those they banned are told so.
'''
import time
from datetime import datetime, timedelta, timezone

from files.tests.spec.harness import *


def test_reverting_an_admin_without_recent_actions_only_logs_it():
	target = factories.admin(2)
	admin = factories.admin(3)

	with db_diff() as d:
		r = as_user(admin).post(f"/@{target['username']}/revert_actions")

	assert_json_message(r)
	d.assert_exactly(inserted={"modactions": [{"kind": "revert", "user_id": admin["id"], "target_user_id": target["id"], "target_submission_id": None, "target_comment_id": None}]})


def _logged(admin, kind, **target):
	db.insert("modactions", user_id=admin["id"], kind=kind, **target)


def test_reverting_restores_what_the_admin_removed_in_the_last_day():
	target = factories.admin(2)
	author = factories.user()
	post = factories.post(author, state_mod="REMOVED", state_mod_set_by=target["username"])
	other_post = factories.post(factories.user())
	comment = factories.comment(author, other_post, state_mod="REMOVED", state_mod_set_by=target["username"])
	_logged(target, "remove_post", target_submission_id=post["id"])
	_logged(target, "remove_comment", target_comment_id=comment["id"])
	admin = factories.admin(3)

	with db_diff() as d:
		r = as_user(admin).post(f"/@{target['username']}/revert_actions")

	assert_json_message(r)
	restored = {"state_mod": "VISIBLE", "state_mod_set_by": admin["username"]}
	d.assert_exactly(
		updated={
			"submissions": {post["id"]: restored, other_post["id"]: {"comment_count": 1}},
			"comments": {comment["id"]: restored},
			"users": {author["id"]: {"post_count": 1, "comment_count": 1}},
		},
		inserted={
			"modactions": [{"kind": "revert", "user_id": admin["id"], "target_user_id": target["id"]}],
			"notifications": [{"user_id": other_post["author_id"], "comment_id": comment["id"]}],
		},
	)


def test_reverting_leaves_items_held_since():
	target = factories.admin(2)
	post = factories.post(factories.user(), state_mod="FILTERED")
	_logged(target, "remove_post", target_submission_id=post["id"])
	admin = factories.admin(3)

	with db_diff() as d:
		r = as_user(admin).post(f"/@{target['username']}/revert_actions")

	assert_json_message(r)
	d.assert_exactly(inserted={"modactions": [{"kind": "revert", "user_id": admin["id"], "target_user_id": target["id"]}]})


def test_reverting_leaves_what_the_admin_did_over_a_day_ago():
	target = factories.admin(2)
	post = factories.post(factories.user(), state_mod="REMOVED")
	db.insert("modactions", user_id=target["id"], kind="remove_post", target_submission_id=post["id"], created_datetimez=datetime.now(timezone.utc) - timedelta(days=1, minutes=1))
	admin = factories.admin(3)

	with db_diff() as d:
		r = as_user(admin).post(f"/@{target['username']}/revert_actions")

	assert_json_message(r)
	d.assert_exactly(inserted={"modactions": [{"kind": "revert", "user_id": admin["id"], "target_user_id": target["id"]}]})


def test_reverting_unbans_whom_the_admin_banned_and_tells_only_them():
	target = factories.admin(2)
	banned = factories.user(is_banned=target["id"], unban_utc=int(time.time()) + 86400, ban_reason=factories.unique("reason"))
	shadowbanned = factories.user(shadowbanned=target["username"])
	_logged(target, "ban_user", target_user_id=banned["id"])
	_logged(target, "shadowban", target_user_id=shadowbanned["id"])
	admin = factories.admin(3)

	with db_diff() as d:
		r = as_user(admin).post(f"/@{target['username']}/revert_actions")

	assert_json_message(r)
	d.assert_exactly(
		updated={"users": {banned["id"]: {"is_banned": 0, "unban_utc": 0, "ban_reason": None}, shadowbanned["id"]: {"shadowbanned": None}}},
		inserted={
			"modactions": [{"kind": "revert", "user_id": admin["id"], "target_user_id": target["id"]}],
			"comments": [{"author_id": seed.SYSTEM_ID, "parent_submission": None}],
			"notifications": [{"user_id": banned["id"]}],
		},
	)


def test_reverting_an_unknown_user_is_not_found():
	admin = factories.admin(3)
	username = factories.unique()

	with db_diff() as d:
		r = as_user(admin).post(f"/@{username}/revert_actions", headers=XHR)

	assert_status(r, 404)
	d.assert_exactly()
