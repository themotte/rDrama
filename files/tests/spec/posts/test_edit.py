'''
Editing a post: POST /edit_post/<id> with "title" and "body" (both sent in full; the link of a link post can't be changed) and optional images in "file" appended to the body. Redirects to the post.
'''
import re

import pytest

from files.tests.spec.harness import *


def _edit(client, post, files=None, **fields):
	return client.post(f"/edit_post/{post['id']}", {"title": post["title"], "body": post["body"], **fields}, headers=XHR, files=files)


def test_author_edits_the_body():
	author = factories.user()
	post = factories.post(author, body="before")

	with db_diff() as d:
		r = _edit(as_user(author), post, body="after")

	assert_redirect(r, f"/post/{post['id']}/{post['title']}")
	d.assert_exactly(updated={"submissions": {post["id"]: {"body": "after", "body_html": ANY}}})
	assert "after" in db.row("submissions", id=post["id"])["body_html"]


def test_author_edits_the_title():
	author = factories.user()
	post = factories.post(author, body="text")
	title = factories.unique("title")

	with db_diff() as d:
		_edit(as_user(author), post, title=title)

	d.assert_exactly(updated={"submissions": {post["id"]: {"title": title, "title_html": title}}})


def test_editing_an_older_post_marks_it_edited():
	'''Edits within the first three minutes after posting go unmarked.'''
	author = factories.user()
	post = factories.post(author, body="before", created_utc=1000)

	with db_diff() as d:
		_edit(as_user(author), post, body="after")

	d.assert_exactly(updated={"submissions": {post["id"]: {"body": "after", "body_html": ANY, "edited_utc": ANY}}})
	assert db.row("submissions", id=post["id"])["edited_utc"] > 1000


def test_an_edit_that_changes_nothing_is_refused():
	author = factories.user()
	post = factories.post(author, body="same")

	with db_diff() as d:
		r = _edit(as_user(author), post)

	assert_status(r, 400)
	d.assert_exactly()


def test_admins_who_may_edit_posts_edit_others_posts_on_the_record():
	post = factories.post(factories.user(), body="before", created_utc=1000)
	editor = factories.admin(3)

	with db_diff() as d:
		r = _edit(as_user(editor), post, body="after")

	assert_redirect(r, f"/post/{post['id']}/{post['title']}")
	d.assert_exactly(
		updated={"submissions": {post["id"]: {"body": "after", "body_html": ANY}}},
		inserted={"modactions": [{"kind": "edit_post", "user_id": editor["id"], "target_submission_id": post["id"]}]},
	)


@pytest.mark.parametrize("level", [0, 2])
def test_others_may_not_edit(level):
	post = factories.post(factories.user(), body="before")
	other = factories.admin(level)

	with db_diff() as d:
		r = _edit(as_user(other), post, body="after")

	assert_status(r, 403)
	d.assert_exactly()


def test_editing_an_unknown_post_is_not_found():
	post = factories.post(factories.user(), body="x")
	db.delete("votes", submission_id=post["id"])
	db.delete("submissions", id=post["id"])

	assert_status(_edit(as_user(factories.user()), post, body="y"), 404)


def test_editing_needs_a_login():
	post = factories.post(factories.user(), body="x")

	assert_api_unauthorized(anon().post(f"/edit_post/{post['id']}", {"title": "t", "body": "y"}, headers=XHR))


def test_edit_images_are_linked_at_the_end_of_the_body():
	author = factories.user()
	post = factories.post(author, body="text")

	with db_diff() as d:
		_edit(as_user(author), post, files={"file": uploads.png(20, 20)})

	d.assert_exactly(updated={"submissions": {post["id"]: {"body": ANY, "body_html": ANY}}})
	body = db.row("submissions", id=post["id"])["body"]
	[image] = {u for u in re.findall(r"/images/[^\s\"<>)]+", body)}
	assert body.startswith("text")
	assert_serves_image(image)
