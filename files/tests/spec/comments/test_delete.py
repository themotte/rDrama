'''
Deleting and restoring your own comments: POST /delete/comment/<comment id> marks the comment deleted (with the time), POST /undelete/comment/<comment id> clears the mark; the comment stops or starts counting (see test_counters.py), and a restored comment notifies those it concerns who weren't notified about it yet, as a new one does. Both answer with a JSON message.

Refused, changing nothing: 409 for deleting a comment already deleted or restoring one that isn't, 403 for someone else's comment whatever its state, 404 for an unknown comment, 401 for anonymous scripts. (Suspended users may delete but not restore; see the users area.)
'''
import pytest

from files.tests.spec.harness import *

DELETED = "2020-01-01T00:00:00Z"


def _own(author=None, **overrides):
	author = author or factories.user()
	return author, factories.comment(author, factories.post(factories.user()), **overrides)


def test_deleting_your_comment_marks_it_deleted():
	author, comment = _own()
	client = as_user(author)

	with db_diff() as d:
		r = client.post(f"/delete/comment/{comment['id']}", headers=XHR)

	assert_json_message(r)
	d.assert_exactly(updated={"comments": {comment["id"]: {"state_user_deleted_utc": ANY}}, "submissions": {comment["parent_submission"]: {"comment_count": 0}}, "users": {author["id"]: {"comment_count": 0}}})
	assert db.row("comments", id=comment["id"])["state_user_deleted_utc"] is not None


def test_restoring_your_comment_clears_the_mark():
	author, comment = _own(state_user_deleted_utc=DELETED)
	client = as_user(author)

	with db_diff() as d:
		r = client.post(f"/undelete/comment/{comment['id']}", headers=XHR)

	assert_json_message(r)
	d.assert_exactly(
		updated={"comments": {comment["id"]: {"state_user_deleted_utc": None}}, "submissions": {comment["parent_submission"]: {"comment_count": 1}}, "users": {author["id"]: {"comment_count": 1}}},
		inserted={"notifications": [{"user_id": db.row("submissions", id=comment["parent_submission"])["author_id"], "comment_id": comment["id"]}]},
	)


@pytest.mark.parametrize("action, state", [
	("delete", {"state_user_deleted_utc": DELETED}),
	("undelete", {}),
])
def test_repeating_on_your_comment_conflicts(action, state):
	author, comment = _own(**state)
	client = as_user(author)

	with db_diff() as d:
		r = client.post(f"/{action}/comment/{comment['id']}", headers=XHR)

	assert_status(r, 409)
	d.assert_exactly()


@pytest.mark.parametrize("actor", ["user", "admin"])
@pytest.mark.parametrize("action, state", [
	("delete", {}),
	("delete", {"state_user_deleted_utc": DELETED}),
	("undelete", {"state_user_deleted_utc": DELETED}),
	("undelete", {}),
])
def test_someone_elses_comment_is_forbidden(action, state, actor):
	_, comment = _own(**state)
	client = as_user(factories.user() if actor == "user" else factories.admin(3))

	with db_diff() as d:
		r = client.post(f"/{action}/comment/{comment['id']}", headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("action", ["delete", "undelete"])
@pytest.mark.parametrize("which", ["unknown", "not an id"])
def test_unknown_comments_are_not_found(action, which):
	cid = db.execute("SELECT nextval('comments_id_seq')") if which == "unknown" else "abc"

	r = as_user(factories.user()).post(f"/{action}/comment/{cid}", headers=XHR)

	assert_status(r, 404)


@pytest.mark.parametrize("action, state", [
	("delete", {}),
	("undelete", {"state_user_deleted_utc": DELETED}),
])
def test_anonymous_scripts_are_unauthorized(action, state):
	_, comment = _own(**state)

	with db_diff() as d:
		r = anon().post(f"/{action}/comment/{comment['id']}", headers=XHR)

	assert_api_unauthorized(r)
	d.assert_exactly()
