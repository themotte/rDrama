'''
Admin marks on posts and comments, all POSTs answering a JSON message:
- /distinguish/<post_id> and /distinguish_comment/<comment_id> toggle the item's distinguish level between the admin's own level and 0. Any admin may distinguish their own post, admins from level 2 anyone's post; comments only their own.
- /sticky/<post_id> and /unsticky/<post_id> pin a post to the top of the front page and take it off, recording which admin pinned it. Pins beyond the third visible one expire an hour after pinning; once its time has passed, a pin counts as unpinned everywhere: the front page, the pages and JSON that show a post as pinned, these routes and the limit, without anything being written.
- /sticky_comment/<comment_id> and /unsticky_comment/<comment_id> pin a comment to the top of its thread and take it off.

Each change is logged in the mod log; pinning or unpinning someone else's item notifies its author. Pinning a pinned item or unpinning an unpinned one changes nothing. An id that isn't an existing item's is 404.
'''
import time

import pytest

from files.tests.spec.harness import *


def _notified(author, admin, post):
	'''The single notification sent, to `author`, names the admin and links the post.'''
	notification = db.row("comments", author_id=seed.SYSTEM_ID, parent_submission=None)
	assert admin["username"] in notification["body_html"]
	assert f"/post/{post['id']}" in notification["body_html"]
	assert db.row("notifications", comment_id=notification["id"])["user_id"] == author["id"]


# Distinguishing posts

@pytest.mark.parametrize("level", [1, 2, 3])
def test_admin_distinguishes_their_own_post_at_their_level(level):
	admin = factories.admin(level)
	post = factories.post(admin)

	with db_diff() as d:
		r = as_user(admin).post(f"/distinguish/{post['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"submissions": {post["id"]: {"distinguish_level": level}}},
		inserted={"modactions": [{"kind": "distinguish_post", "user_id": admin["id"], "target_submission_id": post["id"], "target_user_id": None}]},
	)


@pytest.mark.parametrize("level", [2, 3])
def test_admin_distinguishes_someone_elses_post_from_level_2(level):
	admin = factories.admin(level)
	post = factories.post(factories.user())

	with db_diff() as d:
		r = as_user(admin).post(f"/distinguish/{post['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"submissions": {post["id"]: {"distinguish_level": level}}},
		inserted={"modactions": [{"kind": "distinguish_post", "user_id": admin["id"], "target_submission_id": post["id"]}]},
	)


def test_level_1_admin_cannot_distinguish_someone_elses_post():
	post = factories.post(factories.user())
	admin = factories.admin(1)

	with db_diff() as d:
		r = as_user(admin).post(f"/distinguish/{post['id']}", headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


def test_distinguishing_a_distinguished_post_undistinguishes_it():
	admin = factories.admin(2)
	post = factories.post(factories.user(), distinguish_level=3)

	with db_diff() as d:
		r = as_user(admin).post(f"/distinguish/{post['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"submissions": {post["id"]: {"distinguish_level": 0}}},
		inserted={"modactions": [{"kind": "undistinguish_post", "user_id": admin["id"], "target_submission_id": post["id"]}]},
	)


@pytest.mark.parametrize("action", ["distinguish", "sticky", "unsticky"])
@pytest.mark.parametrize("post_id", ["unknown", "first", "99999999999"])
def test_marking_no_existing_post_is_not_found(action, post_id):
	if post_id == "unknown": post_id = db.execute("SELECT nextval('submissions_id_seq')")
	client = as_user(factories.admin(3))

	with db_diff() as d:
		r = client.post(f"/{action}/{post_id}", headers=XHR)

	assert_status(r, 404)
	d.assert_exactly()


# Distinguishing comments

@pytest.mark.parametrize("level", [1, 3])
def test_admin_distinguishes_their_own_comment_at_their_level(level):
	admin = factories.admin(level)
	comment = factories.comment(admin, factories.post(factories.user()))

	with db_diff() as d:
		r = as_user(admin).post(f"/distinguish_comment/{comment['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"comments": {comment["id"]: {"distinguish_level": level}}},
		inserted={"modactions": [{"kind": "distinguish_comment", "user_id": admin["id"], "target_comment_id": comment["id"], "target_submission_id": None}]},
	)


def test_distinguishing_a_distinguished_comment_undistinguishes_it():
	admin = factories.admin(2)
	comment = factories.comment(admin, factories.post(factories.user()), distinguish_level=2)

	with db_diff() as d:
		r = as_user(admin).post(f"/distinguish_comment/{comment['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"comments": {comment["id"]: {"distinguish_level": 0}}},
		inserted={"modactions": [{"kind": "undistinguish_comment", "user_id": admin["id"], "target_comment_id": comment["id"]}]},
	)


def test_admin_cannot_distinguish_someone_elses_comment():
	comment = factories.comment(factories.user(), factories.post(factories.user()))
	admin = factories.admin(3)

	with db_diff() as d:
		r = as_user(admin).post(f"/distinguish_comment/{comment['id']}", headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


def test_distinguishing_an_unknown_comment_is_not_found():
	comment = factories.comment(factories.user(), factories.post(factories.user()))
	db.delete("commentvotes", comment_id=comment["id"])
	db.delete("comments", id=comment["id"])
	admin = factories.admin(2)

	with db_diff() as d:
		r = as_user(admin).post(f"/distinguish_comment/{comment['id']}", headers=XHR)

	assert_status(r, 404)
	d.assert_exactly()


# Pinning posts

def test_admin_pins_someone_elses_post_and_notifies_its_author():
	author = factories.user()
	post = factories.post(author)
	admin = factories.admin(2)

	with db_diff() as d:
		r = as_user(admin).post(f"/sticky/{post['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"submissions": {post["id"]: {"stickied": admin["username"]}}},
		inserted={
			"modactions": [{"kind": "pin_post", "user_id": admin["id"], "target_submission_id": post["id"]}],
			"comments": [{"author_id": seed.SYSTEM_ID, "parent_submission": None}],
			"notifications": [{"user_id": author["id"]}],
		},
	)
	_notified(author, admin, post)


def test_admin_pins_their_own_post_without_a_notification():
	admin = factories.admin(2)
	post = factories.post(admin)

	with db_diff() as d:
		r = as_user(admin).post(f"/sticky/{post['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"submissions": {post["id"]: {"stickied": admin["username"]}}},
		inserted={"modactions": [{"kind": "pin_post", "user_id": admin["id"], "target_submission_id": post["id"]}]},
	)


def test_pinning_a_pinned_post_changes_nothing():
	post = factories.post(factories.user(), stickied="someadmin")
	admin = factories.admin(2)

	with db_diff() as d:
		r = as_user(admin).post(f"/sticky/{post['id']}")

	assert_json_message(r)
	d.assert_exactly()


def test_a_fourth_pin_expires_after_an_hour():
	for _ in range(3):
		factories.post(factories.user(), stickied="someadmin")
	admin = factories.admin(2)
	post = factories.post(admin)

	with db_diff() as d:
		r = as_user(admin).post(f"/sticky/{post['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"submissions": {post["id"]: {"stickied": admin["username"], "stickied_utc": ANY}}},
		inserted={"modactions": [{"kind": "pin_post", "user_id": admin["id"], "target_submission_id": post["id"]}]},
	)
	expiry = db.row("submissions", id=post["id"])["stickied_utc"]
	assert time.time() + 3600 - 60 <= expiry <= time.time() + 3600


def test_pins_on_posts_others_cannot_see_do_not_count_toward_the_limit():
	for state in ["VISIBLE", "VISIBLE", "REMOVED", "FILTERED"]:
		factories.post(factories.user(), stickied="someadmin", state_mod=state)
	admin = factories.admin(2)
	post = factories.post(admin)

	with db_diff() as d:
		r = as_user(admin).post(f"/sticky/{post['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"submissions": {post["id"]: {"stickied": admin["username"]}}},
		inserted={"modactions": [{"kind": "pin_post", "user_id": admin["id"], "target_submission_id": post["id"]}]},
	)


def _expired_pin(author, pinner):
	return factories.post(author, stickied=pinner, stickied_utc=int(time.time()) - 60)


def test_pinning_an_expired_pin_pins_it_again_without_an_expiry():
	admin = factories.admin(2)
	post = _expired_pin(admin, "someadmin")

	with db_diff() as d:
		r = as_user(admin).post(f"/sticky/{post['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"submissions": {post["id"]: {"stickied": admin["username"], "stickied_utc": None}}},
		inserted={"modactions": [{"kind": "pin_post", "user_id": admin["id"], "target_submission_id": post["id"]}]},
	)


def test_expired_pins_do_not_count_toward_the_limit():
	for _ in range(3):
		_expired_pin(factories.user(), "someadmin")
	admin = factories.admin(2)
	post = factories.post(admin)

	with db_diff() as d:
		r = as_user(admin).post(f"/sticky/{post['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"submissions": {post["id"]: {"stickied": admin["username"]}}},
		inserted={"modactions": [{"kind": "pin_post", "user_id": admin["id"], "target_submission_id": post["id"]}]},
	)


def test_unpinning_an_expired_pin_changes_nothing():
	post = _expired_pin(factories.user(), "someadmin")
	client = as_user(factories.admin(2))

	with db_diff() as d:
		r = client.post(f"/unsticky/{post['id']}")

	assert_json_message(r)
	d.assert_exactly()


def test_a_pin_within_its_time_is_still_pinned():
	admin = factories.admin(2)
	post = factories.post(factories.user(), stickied="someadmin", stickied_utc=int(time.time()) + 600)

	with db_diff() as d:
		r = as_user(admin).post(f"/sticky/{post['id']}")

	assert_json_message(r)
	d.assert_exactly()


@pytest.mark.parametrize("expired", [False, True])
def test_post_json_names_the_pinner_while_pinned(expired):
	post = factories.post(factories.user(), stickied="someadmin", stickied_utc=int(time.time()) + (-60 if expired else 3600))

	r = as_api(factories.api_token(factories.user())).get(f"/post/{post['id']}")

	assert r.json["stickied"] == (None if expired else "someadmin")


@pytest.mark.parametrize("page", ["post page", "front page"])
@pytest.mark.parametrize("expired", [False, True])
def test_pages_show_the_pinner_only_while_pinned(page, expired):
	pinner = factories.unique("pinner")
	post = factories.post(factories.user(), stickied=pinner, stickied_utc=int(time.time()) + (-60 if expired else 3600))

	r = anon().get(f"/post/{post['id']}" if page == "post page" else "/")

	assert_in_payload(r, post["title"])
	(assert_not_in_payload if expired else assert_in_payload)(r, pinner)


def test_admin_unpins_someone_elses_post_and_notifies_its_author():
	author = factories.user()
	post = factories.post(author, stickied="someadmin", stickied_utc=int(time.time()) + 3600)
	admin = factories.admin(2)

	with db_diff() as d:
		r = as_user(admin).post(f"/unsticky/{post['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"submissions": {post["id"]: {"stickied": None, "stickied_utc": None}}},
		inserted={
			"modactions": [{"kind": "unpin_post", "user_id": admin["id"], "target_submission_id": post["id"]}],
			"comments": [{"author_id": seed.SYSTEM_ID, "parent_submission": None}],
			"notifications": [{"user_id": author["id"]}],
		},
	)
	_notified(author, admin, post)


def test_admin_unpins_their_own_post_without_a_notification():
	admin = factories.admin(2)
	post = factories.post(admin, stickied=admin["username"])

	with db_diff() as d:
		r = as_user(admin).post(f"/unsticky/{post['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"submissions": {post["id"]: {"stickied": None}}},
		inserted={"modactions": [{"kind": "unpin_post", "user_id": admin["id"], "target_submission_id": post["id"]}]},
	)


def test_unpinning_an_unpinned_post_changes_nothing():
	post = factories.post(factories.user())
	admin = factories.admin(2)

	with db_diff() as d:
		r = as_user(admin).post(f"/unsticky/{post['id']}")

	assert_json_message(r)
	d.assert_exactly()


# Pinning comments

def test_admin_pins_someone_elses_comment_and_notifies_its_author():
	author = factories.user()
	post = factories.post(factories.user())
	comment = factories.comment(author, post)
	admin = factories.admin(2)

	with db_diff() as d:
		r = as_user(admin).post(f"/sticky_comment/{comment['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"comments": {comment["id"]: {"is_pinned": admin["username"]}}},
		inserted={
			"modactions": [{"kind": "pin_comment", "user_id": admin["id"], "target_comment_id": comment["id"]}],
			"comments": [{"author_id": seed.SYSTEM_ID, "parent_submission": None}],
			"notifications": [{"user_id": author["id"]}],
		},
	)
	_notified(author, admin, post)


def test_admin_pins_their_own_comment_without_a_notification():
	admin = factories.admin(2)
	comment = factories.comment(admin, factories.post(factories.user()))

	with db_diff() as d:
		r = as_user(admin).post(f"/sticky_comment/{comment['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"comments": {comment["id"]: {"is_pinned": admin["username"]}}},
		inserted={"modactions": [{"kind": "pin_comment", "user_id": admin["id"], "target_comment_id": comment["id"]}]},
	)


def test_pinning_a_pinned_comment_changes_nothing():
	comment = factories.comment(factories.user(), factories.post(factories.user()), is_pinned="someadmin")
	admin = factories.admin(2)

	with db_diff() as d:
		r = as_user(admin).post(f"/sticky_comment/{comment['id']}")

	assert_json_message(r)
	d.assert_exactly()


def test_admin_unpins_someone_elses_comment_and_notifies_its_author():
	author = factories.user()
	post = factories.post(factories.user())
	comment = factories.comment(author, post, is_pinned="someadmin")
	admin = factories.admin(2)

	with db_diff() as d:
		r = as_user(admin).post(f"/unsticky_comment/{comment['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"comments": {comment["id"]: {"is_pinned": None}}},
		inserted={
			"modactions": [{"kind": "unpin_comment", "user_id": admin["id"], "target_comment_id": comment["id"]}],
			"comments": [{"author_id": seed.SYSTEM_ID, "parent_submission": None}],
			"notifications": [{"user_id": author["id"]}],
		},
	)
	_notified(author, admin, post)


def test_admin_unpins_their_own_comment_without_a_notification():
	admin = factories.admin(2)
	comment = factories.comment(admin, factories.post(factories.user()), is_pinned=admin["username"])

	with db_diff() as d:
		r = as_user(admin).post(f"/unsticky_comment/{comment['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"comments": {comment["id"]: {"is_pinned": None}}},
		inserted={"modactions": [{"kind": "unpin_comment", "user_id": admin["id"], "target_comment_id": comment["id"]}]},
	)


def test_unpinning_an_unpinned_comment_changes_nothing():
	comment = factories.comment(factories.user(), factories.post(factories.user()))
	admin = factories.admin(2)

	with db_diff() as d:
		r = as_user(admin).post(f"/unsticky_comment/{comment['id']}")

	assert_json_message(r)
	d.assert_exactly()


@pytest.mark.parametrize("action", ["sticky_comment", "unsticky_comment"])
def test_pinning_an_unknown_comment_is_not_found(action):
	comment = factories.comment(factories.user(), factories.post(factories.user()))
	db.delete("commentvotes", comment_id=comment["id"])
	db.delete("comments", id=comment["id"])
	admin = factories.admin(2)

	with db_diff() as d:
		r = as_user(admin).post(f"/{action}/{comment['id']}", headers=XHR)

	assert_status(r, 404)
	d.assert_exactly()
