'''
What suspended users may do. While a ban runs (permanently, or until its end time), a user can't change anything other users see. Each of these is refused with 403 and changes nothing:
- their posts and comments: publishing a draft (POST /publish/<post id>), editing (POST /edit_post/<post id>, POST /edit_comment/<comment id>), restoring deleted ones (POST /undelete_post/<post id>, POST /undelete/comment/<comment id>), marking them NSFW (POST /toggle_post_nsfw/<post id>, POST /toggle_comment_nsfw/<comment id>), pinning a post to their profile (POST /pin/<post id>), and pinning or unpinning comments on their posts (POST /pin_comment/<comment id>, POST /unpin_comment/<comment id>);
(Posting and commenting are refused too; see the posts and comments areas.)

Everything else still works: deleting their own content, saving, subscribing, unfollowing, removing followers, blocking, and their private preferences. Once a temporary ban has run out, nothing is refused.
'''
import time

import pytest

from files.tests.spec.harness import *

DELETED = "2020-01-01T00:00:00Z"


def _suspended(**overrides):
	return factories.user(is_banned=factories.admin(2)["id"], unban_utc=int(time.time()) + 86400, **overrides)


def _expired(**overrides):
	return factories.user(is_banned=factories.admin(2)["id"], unban_utc=int(time.time()) - 60, **overrides)


def _own_comment(v, **overrides):
	return factories.comment(v, factories.post(factories.user()), **overrides)


def _others_comment_on_own_post(v, **overrides):
	return factories.comment(factories.user(), factories.post(v), **overrides)


# Each case builds what the request needs for the suspended user `v` and returns (path, form fields, files)
CONTENT = {
	"publish": lambda v: (f"/publish/{factories.post(v, private=True)['id']}", {}, None),
	"edit post": lambda v: (lambda p: (f"/edit_post/{p['id']}", {"title": p["title"], "body": factories.unique()}, None))(factories.post(v)),
	"undelete post": lambda v: (f"/undelete_post/{factories.post(v, state_user_deleted_utc=DELETED)['id']}", {}, None),
	"post nsfw": lambda v: (f"/toggle_post_nsfw/{factories.post(v)['id']}", {}, None),
	"comment nsfw": lambda v: (f"/toggle_comment_nsfw/{_own_comment(v)['id']}", {}, None),
	"pin post": lambda v: (f"/pin/{factories.post(v)['id']}", {}, None),
	"edit comment": lambda v: (f"/edit_comment/{_own_comment(v)['id']}", {"body": factories.unique()}, None),
	"undelete comment": lambda v: (f"/undelete/comment/{_own_comment(v, state_user_deleted_utc=DELETED)['id']}", {}, None),
	"pin comment": lambda v: (f"/pin_comment/{_others_comment_on_own_post(v)['id']}", {}, None),
	"unpin comment": lambda v: (f"/unpin_comment/{_others_comment_on_own_post(v, is_pinned=v['username'] + ' (OP)')['id']}", {}, None),
}

def _refused(case):
	v = _suspended()
	path, fields, files = case(v)
	client = as_user(v)

	with db_diff() as d:
		r = client.post(path, fields, headers=XHR, files=files)

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("name", CONTENT)
def test_suspended_users_cant_change_their_content(name):
	_refused(CONTENT[name])


def test_suspended_users_can_still_delete_their_posts():
	v = _suspended()
	post = factories.post(v)
	client = as_user(v)

	with db_diff() as d:
		r = client.post(f"/delete_post/{post['id']}", headers=XHR)

	assert_status(r, 200)
	d.assert_exactly(updated={"submissions": {post["id"]: {"state_user_deleted_utc": ANY}}, "users": {v["id"]: {"post_count": 0}}})


def test_suspended_users_can_still_save_posts():
	v = _suspended()
	post = factories.post(factories.user())
	client = as_user(v)

	with db_diff() as d:
		r = client.post(f"/save_post/{post['id']}", headers=XHR)

	assert_status(r, 200)
	d.assert_exactly(inserted={"save_relationship": [{"user_id": v["id"], "submission_id": post["id"]}]})


def test_suspended_users_can_still_change_private_preferences():
	v = _suspended(hidevotedon=False)
	client = as_user(v)

	with db_diff() as d:
		r = client.post("/settings/profile", {"hidevotedon": "true"}, headers=XHR)

	assert_status(r, 200)
	d.assert_exactly(updated={"users": {v["id"]: {"hidevotedon": True}}})


def test_users_whose_ban_ran_out_can_edit_their_posts():
	v = _expired()
	post = factories.post(v)
	client = as_user(v)

	with db_diff() as d:
		r = client.post(f"/edit_post/{post['id']}", {"title": post["title"], "body": "after"})

	assert_redirect(r, f"/post/{post['id']}/{post['title']}")
	d.assert_exactly(updated={"submissions": {post["id"]: {"body": "after", "body_html": ANY}}})
