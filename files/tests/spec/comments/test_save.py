'''
Saving comments: POST /save_comment/<comment id> adds the comment to the viewer's saved comments (see the users area for the list), POST /unsave_comment/<comment id> takes it off. Both answer with a JSON message, and both are idempotent: saving a saved comment or unsaving one that isn't saved succeeds and changes nothing.

Only comments on posts the viewer can see can be saved: saving a private message (the viewer's own included) or a comment on someone else's draft is refused with 404, as for an unknown comment. Unsaving a saved comment always works, even one the viewer can no longer see; unsaving an unsaved comment the viewer can't see is 404.

Refused: 404 for an unknown comment, 401 for anonymous scripts.
'''
import pytest

from files.tests.spec.harness import *


def _comment():
	return factories.comment(factories.user(), factories.post(factories.user()))


def test_saving_a_comment():
	viewer, comment = factories.user(), _comment()
	client = as_user(viewer)

	with db_diff() as d:
		r = client.post(f"/save_comment/{comment['id']}", headers=XHR)

	assert_json_message(r)
	d.assert_exactly(inserted={"comment_save_relationship": [{"user_id": viewer["id"], "comment_id": comment["id"]}]})


def test_saving_a_saved_comment_changes_nothing():
	viewer, comment = factories.user(), _comment()
	db.insert("comment_save_relationship", user_id=viewer["id"], comment_id=comment["id"])
	client = as_user(viewer)

	with db_diff() as d:
		r = client.post(f"/save_comment/{comment['id']}", headers=XHR)

	assert_json_message(r)
	d.assert_exactly()


def test_unsaving_a_comment():
	viewer, comment = factories.user(), _comment()
	db.insert("comment_save_relationship", user_id=viewer["id"], comment_id=comment["id"])
	other = factories.user()
	db.insert("comment_save_relationship", user_id=other["id"], comment_id=comment["id"])
	client = as_user(viewer)

	with db_diff() as d:
		r = client.post(f"/unsave_comment/{comment['id']}", headers=XHR)

	assert_json_message(r)
	d.assert_exactly(deleted={"comment_save_relationship": [(viewer["id"], comment["id"])]})


def test_unsaving_a_comment_not_saved_changes_nothing():
	viewer, comment = factories.user(), _comment()
	db.insert("comment_save_relationship", user_id=factories.user()["id"], comment_id=comment["id"])
	client = as_user(viewer)

	with db_diff() as d:
		r = client.post(f"/unsave_comment/{comment['id']}", headers=XHR)

	assert_json_message(r)
	d.assert_exactly()


@pytest.mark.parametrize("action", ["save_comment", "unsave_comment"])
@pytest.mark.parametrize("which", ["unknown", "not an id"])
def test_unknown_comments_are_not_found(action, which):
	cid = db.execute("SELECT nextval('comments_id_seq')") if which == "unknown" else "abc"
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.post(f"/{action}/{cid}", headers=XHR)

	assert_status(r, 404)
	d.assert_exactly()


@pytest.mark.parametrize("action", ["save_comment", "unsave_comment"])
def test_anonymous_scripts_are_unauthorized(action):
	comment = _comment()

	with db_diff() as d:
		r = anon().post(f"/{action}/{comment['id']}", headers=XHR)

	assert_api_unauthorized(r)
	d.assert_exactly()


def _message(author, recipient):
	return factories.message(author, recipient, created_utc=1000)


def _unsaveable(kind, viewer):
	if kind == "others' message": return _message(factories.user(), factories.user())
	if kind == "own message": return _message(viewer, factories.user())
	return factories.comment(factories.user(), factories.post(factories.user(), private=True))


UNSAVEABLE = ["others' message", "own message", "comment on others' draft"]


@pytest.mark.parametrize("kind", UNSAVEABLE)
def test_saving_what_the_viewer_cant_see_on_a_post_is_not_found(kind):
	viewer = factories.user()
	comment = _unsaveable(kind, viewer)
	client = as_user(viewer)

	with db_diff() as d:
		r = client.post(f"/save_comment/{comment['id']}", headers=XHR)

	assert_status(r, 404)
	d.assert_exactly()


def test_saving_a_comment_on_the_viewers_own_draft():
	viewer = factories.user()
	comment = factories.comment(factories.user(), factories.post(viewer, private=True))
	client = as_user(viewer)

	with db_diff() as d:
		r = client.post(f"/save_comment/{comment['id']}", headers=XHR)

	assert_json_message(r)
	d.assert_exactly(inserted={"comment_save_relationship": [{"user_id": viewer["id"], "comment_id": comment["id"]}]})


@pytest.mark.parametrize("kind", UNSAVEABLE)
def test_unsaving_a_saved_comment_the_viewer_cant_see(kind):
	viewer = factories.user()
	comment = _unsaveable(kind, viewer)
	db.insert("comment_save_relationship", user_id=viewer["id"], comment_id=comment["id"])
	client = as_user(viewer)

	with db_diff() as d:
		r = client.post(f"/unsave_comment/{comment['id']}", headers=XHR)

	assert_json_message(r)
	d.assert_exactly(deleted={"comment_save_relationship": [(viewer["id"], comment["id"])]})


@pytest.mark.parametrize("kind", UNSAVEABLE)
def test_unsaving_an_unsaved_comment_the_viewer_cant_see_is_not_found(kind):
	viewer = factories.user()
	comment = _unsaveable(kind, viewer)
	client = as_user(viewer)

	with db_diff() as d:
		r = client.post(f"/unsave_comment/{comment['id']}", headers=XHR)

	assert_status(r, 404)
	d.assert_exactly()
