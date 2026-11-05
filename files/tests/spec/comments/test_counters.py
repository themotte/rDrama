'''
The comment counts the site keeps, and what they count:
- a post's comment count: its comments others can see, meaning not held for review or removed, not deleted by their author, and not by a shadowbanned user;
- a comment's descendant count: comments others can see anywhere below it in its thread, whatever the state of the comments in between;
- a user's comment count: their comments that aren't held for review, removed or deleted.

Every way a comment's visibility changes keeps these exact.
'''
import pytest

from files.tests.spec.harness import *

DELETED = "2020-01-01T00:00:00Z"

_COUNTED = "c.parent_submission IS NOT NULL AND c.state_mod = 'VISIBLE' AND c.state_user_deleted_utc IS NULL AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id = c.author_id AND u.shadowbanned IS NOT NULL)"


def assert_counts_exact(post, *users):
	'''The stored counts of `post`, its comments and `users` equal a recount by their definitions.'''
	assert db.row("submissions", id=post["id"])["comment_count"] == db.execute(f"SELECT count(*) FROM comments c WHERE c.parent_submission = :post AND {_COUNTED}", post=post["id"])
	for comment in db.rows("comments", parent_submission=post["id"]):
		below = db.execute(f"""
			WITH RECURSIVE below(id) AS (
				SELECT id FROM comments WHERE parent_comment_id = :id
				UNION ALL
				SELECT c.id FROM comments c JOIN below b ON c.parent_comment_id = b.id
			)
			SELECT count(*) FROM comments c WHERE c.id IN (SELECT id FROM below) AND {_COUNTED}
		""", id=comment["id"])
		assert comment["descendant_count"] == below, f"comment {comment['id']}"
	for user in users:
		assert db.row("users", id=user["id"])["comment_count"] == db.execute("SELECT count(*) FROM comments c JOIN submissions s ON s.id = c.parent_submission WHERE c.author_id = :id AND c.state_mod = 'VISIBLE' AND c.state_user_deleted_utc IS NULL AND NOT s.private", id=user["id"]), f"user {user['id']}"


def _thread(author):
	'''A post with a comment by `author` two replies deep, under two comments by others.'''
	post = factories.post(factories.user())
	top = factories.comment(factories.user(), post)
	middle = factories.comment(factories.user(), post, parent=top)
	comment = factories.comment(author, post, parent=middle)
	return post, comment


# Deleting and restoring

def test_deleting_a_comment_uncounts_it():
	author = factories.user()
	post, comment = _thread(author)

	assert_json_message(as_user(author).post(f"/delete/comment/{comment['id']}", headers=XHR))

	assert_counts_exact(post, author)
	assert db.row("submissions", id=post["id"])["comment_count"] == 2


def test_restoring_a_comment_counts_it_again():
	author = factories.user()
	post, comment = _thread(author)
	client = as_user(author)
	assert_json_message(client.post(f"/delete/comment/{comment['id']}", headers=XHR))

	assert_json_message(client.post(f"/undelete/comment/{comment['id']}", headers=XHR))

	assert_counts_exact(post, author)
	assert db.row("submissions", id=post["id"])["comment_count"] == 3


def test_restoring_a_comment_doesnt_notify_anyone_twice():
	author, mentioned = factories.user(), factories.user()
	post = factories.post(factories.user())
	client = as_user(author)
	assert_status(client.post("/comment", {"parent_fullname": f"post_{post['id']}", "body": f"hi @{mentioned['username']}"}, headers=XHR), 200)
	comment = db.rows("comments", author_id=author["id"])[-1]
	assert_json_message(client.post(f"/delete/comment/{comment['id']}", headers=XHR))
	notifications = db.rows("notifications", comment_id=comment["id"])
	assert len(notifications) == 2

	assert_json_message(client.post(f"/undelete/comment/{comment['id']}", headers=XHR))

	assert db.rows("notifications", comment_id=comment["id"]) == notifications


@pytest.mark.parametrize("state", [{"state_mod": "REMOVED", "state_mod_set_by": "somemod"}, {"state_mod": "FILTERED"}], ids=["removed", "held"])
def test_deleting_and_restoring_an_uncounted_comment_counts_nothing(state):
	author = factories.user()
	post = factories.post(factories.user())
	comment = factories.comment(author, post, **state)
	client = as_user(author)

	assert_json_message(client.post(f"/delete/comment/{comment['id']}", headers=XHR))
	assert_counts_exact(post, author)
	assert_json_message(client.post(f"/undelete/comment/{comment['id']}", headers=XHR))
	assert_counts_exact(post, author)


# Moderation

def _moderate(comment, new_status):
	r = as_user(factories.admin(2)).post_json("/admin/update_filter_status", {"new_status": new_status, "comment_id": comment["id"]})
	assert_status(r, 200)


@pytest.mark.parametrize("state, new_status", [
	({"state_user_deleted_utc": DELETED}, "removed"),
	({"state_user_deleted_utc": DELETED, "state_mod": "REMOVED", "state_mod_set_by": "somemod"}, "normal"),
	({"state_user_deleted_utc": DELETED, "state_mod": "FILTERED"}, "normal"),
], ids=["removing a deleted comment", "approving a removed deleted comment", "approving a held deleted comment"])
def test_moderating_a_deleted_comment_counts_nothing(state, new_status):
	author = factories.user()
	post, comment = _thread(author)
	db.update("comments", {"id": comment["id"]}, **state)
	db.update("submissions", {"id": post["id"]}, comment_count=2)
	for ancestor in db.rows("comments", parent_submission=post["id"]):
		if ancestor["id"] != comment["id"]:
			db.update("comments", {"id": ancestor["id"]}, descendant_count=ancestor["descendant_count"] - 1)
	db.update("users", {"id": author["id"]}, comment_count=0)

	_moderate(comment, new_status)

	assert_counts_exact(post, author)


@pytest.mark.parametrize("new_status", ["removed", "normal"])
def test_moderating_a_shadowbanned_users_comment_counts_nothing(new_status):
	author = factories.user(shadowbanned="somemod")
	post, comment = _thread(author)
	if new_status == "normal":
		db.update("comments", {"id": comment["id"]}, state_mod="REMOVED", state_mod_set_by="somemod")
		db.update("users", {"id": author["id"]}, comment_count=0)

	_moderate(comment, new_status)

	assert_counts_exact(post)
	assert db.row("submissions", id=post["id"])["comment_count"] == 2


def test_nuking_and_unnuking_a_shadowbanned_user_keeps_counts_exact():
	author = factories.user(shadowbanned="somemod")
	post, _ = _thread(author)
	admin = as_user(factories.admin(3))

	assert_status(admin.post("/admin/nuke_user", {"user": author["username"]}), 302)
	assert_counts_exact(post)
	assert_status(admin.post("/admin/unnuke_user", {"user": author["username"]}), 302)
	assert_counts_exact(post)
