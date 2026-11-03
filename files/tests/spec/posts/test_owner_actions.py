'''
A post's owner actions, all POSTs answering JSON: /publish/<id> (drafts), /delete_post/<id> and /undelete_post/<id>, /pin/<id> (to the author's profile), /toggle_post_nsfw/<id> and /toggle_comment_nsfw/<id>, /save_post/<id> and /unsave_post/<id>.
'''
import pytest

from files.tests.spec.harness import *


def _path(post):
	return f"/post/{post['id']}/{post['title']}"


# Publishing drafts

def test_author_publishes_a_draft():
	author = factories.user()
	draft = factories.post(author, private=True, created_utc=1000)

	with db_diff() as d:
		r = as_user(author).post(f"/publish/{draft['id']}")

	assert_redirect(r, _path(draft))
	d.assert_exactly(updated={"submissions": {draft["id"]: {"private": False, "created_utc": ANY}}})
	assert db.row("submissions", id=draft["id"])["created_utc"] > 1000


def test_publishing_a_draft_notifies_mentioned_users_and_followers():
	mentioned, follower = factories.user(), factories.user()
	author = factories.user()
	db.insert("follows", user_id=follower["id"], target_id=author["id"])
	draft = factories.post(author, private=True, body=f"hello @{mentioned['username']}", created_utc=1000)

	with db_diff() as d:
		as_user(author).post(f"/publish/{draft['id']}")

	d.assert_exactly(
		updated={"submissions": {draft["id"]: {"private": False, "created_utc": ANY}}},
		inserted={
			"comments": [{"author_id": seed.SYSTEM_ID, "parent_submission": None}, {"author_id": seed.AUTOJANNY_ID, "parent_submission": None}],
			"notifications": [{"user_id": mentioned["id"]}, {"user_id": follower["id"]}],
		},
	)


def test_publishing_someone_elses_draft_is_forbidden():
	draft = factories.post(factories.user(), private=True)
	other = factories.user()

	with db_diff() as d:
		r = as_user(other).post(f"/publish/{draft['id']}", headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


def test_publishing_an_already_public_post_changes_nothing():
	author = factories.user()
	post = factories.post(author)

	with db_diff() as d:
		r = as_user(author).post(f"/publish/{post['id']}")

	assert_json_message(r)
	d.assert_exactly()


# Deleting

def test_author_deletes_a_post():
	author = factories.user()
	post = factories.post(author, is_pinned=True, stickied="someadmin")

	with db_diff() as d:
		r = as_user(author).post(f"/delete_post/{post['id']}")

	assert_json_message(r)
	d.assert_exactly(updated={"submissions": {post["id"]: {"state_user_deleted_utc": ANY, "is_pinned": False, "stickied": None}}})
	assert db.row("submissions", id=post["id"])["state_user_deleted_utc"] is not None


def test_author_undeletes_a_post():
	author = factories.user()
	post = factories.post(author)
	as_user(author).post(f"/delete_post/{post['id']}")

	with db_diff() as d:
		r = as_user(author).post(f"/undelete_post/{post['id']}")

	assert_json_message(r)
	d.assert_exactly(updated={"submissions": {post["id"]: {"state_user_deleted_utc": None}}})


@pytest.mark.parametrize("action", ["delete_post", "undelete_post", "pin", "toggle_post_nsfw"])
def test_owner_actions_by_others_are_forbidden(action):
	post = factories.post(factories.user())
	other = factories.user()

	with db_diff() as d:
		r = as_user(other).post(f"/{action}/{post['id']}", headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("action", ["publish", "delete_post", "undelete_post", "pin", "toggle_post_nsfw", "save_post", "unsave_post"])
def test_owner_actions_on_an_unknown_post_are_not_found(action):
	post = factories.post(factories.user())
	db.delete("votes", submission_id=post["id"])
	db.delete("submissions", id=post["id"])

	r = as_user(factories.user()).post(f"/{action}/{post['id']}", headers=XHR)

	assert_status(r, 404)


@pytest.mark.parametrize("action", ["publish", "delete_post", "undelete_post", "pin", "toggle_post_nsfw", "toggle_comment_nsfw", "save_post", "unsave_post"])
def test_owner_actions_need_a_login(action):
	post = factories.post(factories.user())

	r = anon().post(f"/{action}/{post['id']}", headers=XHR)

	assert_api_unauthorized(r)


# Pinning to the author's profile

def test_author_pins_and_unpins_a_post():
	author = factories.user()
	post = factories.post(author)

	with db_diff() as d:
		r = as_user(author).post(f"/pin/{post['id']}")
	assert_json_message(r)
	d.assert_exactly(updated={"submissions": {post["id"]: {"is_pinned": True}}})

	with db_diff() as d:
		r = as_user(author).post(f"/pin/{post['id']}")
	assert_json_message(r)
	d.assert_exactly(updated={"submissions": {post["id"]: {"is_pinned": False}}})


# Marking posts 18+

def test_author_marks_and_unmarks_a_post_18_plus():
	author = factories.user()
	post = factories.post(author)

	with db_diff() as d:
		r = as_user(author).post(f"/toggle_post_nsfw/{post['id']}")
	assert_json_message(r)
	d.assert_exactly(updated={"submissions": {post["id"]: {"over_18": True}}})

	with db_diff() as d:
		as_user(author).post(f"/toggle_post_nsfw/{post['id']}")
	d.assert_exactly(updated={"submissions": {post["id"]: {"over_18": False}}})


@pytest.mark.parametrize("starting, kind", [(False, "set_nsfw"), (True, "unset_nsfw")])
def test_moderator_toggling_someone_elses_post_is_logged(starting, kind):
	post = factories.post(factories.user(), over_18=starting)
	mod = factories.admin(2)

	with db_diff() as d:
		r = as_user(mod).post(f"/toggle_post_nsfw/{post['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"submissions": {post["id"]: {"over_18": not starting}}},
		inserted={"modactions": [{"kind": kind, "user_id": mod["id"], "target_submission_id": post["id"]}]},
	)


def test_moderator_toggling_their_own_post_is_not_logged():
	mod = factories.admin(2)
	post = factories.post(mod)

	with db_diff() as d:
		as_user(mod).post(f"/toggle_post_nsfw/{post['id']}")

	d.assert_exactly(updated={"submissions": {post["id"]: {"over_18": True}}})


def test_below_moderator_level_toggling_someone_elses_post_is_forbidden():
	post = factories.post(factories.user())

	r = as_user(factories.admin(1)).post(f"/toggle_post_nsfw/{post['id']}", headers=XHR)

	assert_status(r, 403)


@pytest.mark.parametrize("who", ["author", "moderator"])
def test_comment_18_plus_toggles(who):
	author = factories.user()
	comment = factories.comment(author, factories.post(factories.user()))
	actor = author if who == "author" else factories.admin(2)

	with db_diff() as d:
		r = as_user(actor).post(f"/toggle_comment_nsfw/{comment['id']}")
	assert_json_message(r)
	d.assert_exactly(updated={"comments": {comment["id"]: {"over_18": True}}})

	with db_diff() as d:
		as_user(actor).post(f"/toggle_comment_nsfw/{comment['id']}")
	d.assert_exactly(updated={"comments": {comment["id"]: {"over_18": False}}})


def test_toggling_someone_elses_comment_is_forbidden():
	comment = factories.comment(factories.user(), factories.post(factories.user()))
	helper = factories.admin(1)

	with db_diff() as d:
		r = as_user(helper).post(f"/toggle_comment_nsfw/{comment['id']}", headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


# Saving

def test_saving_is_idempotent():
	post = factories.post(factories.user())
	u = factories.user()

	with db_diff() as d:
		assert_json_message(as_user(u).post(f"/save_post/{post['id']}"))
	d.assert_exactly(inserted={"save_relationship": [{"user_id": u["id"], "submission_id": post["id"]}]})

	with db_diff() as d:
		assert_json_message(as_user(u).post(f"/save_post/{post['id']}"))
	d.assert_exactly()


def test_unsaving_is_idempotent():
	post = factories.post(factories.user())
	u = factories.user()
	db.insert("save_relationship", user_id=u["id"], submission_id=post["id"])

	with db_diff() as d:
		assert_json_message(as_user(u).post(f"/unsave_post/{post['id']}"))
	d.assert_exactly(deleted={"save_relationship": [(u["id"], post["id"])]})

	with db_diff() as d:
		assert_json_message(as_user(u).post(f"/unsave_post/{post['id']}"))
	d.assert_exactly()
