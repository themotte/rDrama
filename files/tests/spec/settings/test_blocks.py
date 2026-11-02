'''
Blocking: POST /settings/block and /settings/unblock (field "username", matched case-insensitively against current or original usernames), and the GET /settings/blocks list.
'''
import pytest

from files.tests.spec.harness import *


def test_block_user():
	target = factories.user()
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).post("/settings/block", {"username": target["username"].upper()})

	assert_json_message(r)
	d.assert_exactly(inserted={"userblocks": [{"user_id": u["id"], "target_id": target["id"]}]})


def test_block_user_by_original_username():
	target = factories.user(original_username=factories.unique("formerly"))
	u = factories.user()

	assert_json_message(as_user(u).post("/settings/block", {"username": target["original_username"]}))


def test_blocked_users_are_listed_on_the_blocks_page():
	target = factories.user()
	u = factories.user()
	db.insert("userblocks", user_id=u["id"], target_id=target["id"])

	assert_in_payload(as_user(u).get("/settings/blocks"), target["username"])


@pytest.mark.parametrize("username", [None, "nobody-by-this-name"])
def test_blocking_an_unknown_user_is_not_found(username):
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).post("/settings/block", {} if username is None else {"username": username}, headers=XHR)

	assert_status(r, 404)
	d.assert_exactly()


def test_blocking_yourself_is_refused():
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).post("/settings/block", {"username": u["username"]}, headers=XHR)

	assert_status(r, 409)
	d.assert_exactly()


def test_blocking_twice_is_refused():
	target = factories.user()
	u = factories.user()
	db.insert("userblocks", user_id=u["id"], target_id=target["id"])

	with db_diff() as d:
		r = as_user(u).post("/settings/block", {"username": target["username"]}, headers=XHR)

	assert_status(r, 409)
	d.assert_exactly()


def test_the_system_account_cannot_be_blocked():
	u = factories.user()
	system_name = db.row("users", id=seed.SYSTEM_ID)["username"]

	with db_diff() as d:
		r = as_user(u).post("/settings/block", {"username": system_name}, headers=XHR)

	assert_status(r, 409)
	d.assert_exactly()


def test_unblock_user():
	target = factories.user()
	u = factories.user()
	db.insert("userblocks", user_id=u["id"], target_id=target["id"])

	with db_diff() as d:
		r = as_user(u).post("/settings/unblock", {"username": target["username"]})

	assert_json_message(r)
	d.assert_exactly(deleted={"userblocks": [(u["id"], target["id"])]})


def test_unblocking_someone_not_blocked_is_refused():
	target = factories.user()
	u = factories.user()

	assert_status(as_user(u).post("/settings/unblock", {"username": target["username"]}, headers=XHR), 409)


def test_unblocking_an_unknown_user_is_not_found():
	assert_status(as_user(factories.user()).post("/settings/unblock", {"username": "nobody-by-this-name"}, headers=XHR), 404)
