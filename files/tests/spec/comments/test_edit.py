'''
Editing a comment: POST /edit_comment/<comment id> with "body" (markdown; surrounding whitespace is trimmed and it is cut to 500,000 characters). Only the comment's author may edit it, including while it is removed or held for review.

The body and its rendering are replaced; the comment is marked as edited (with the time) only when it is more than 3 minutes old. Requests through Tor have their uploads ("file") dropped. Sending the body unchanged and no file changes nothing.

When the comment is published (visible, not deleted, by an author who isn't shadowbanned, on a post that isn't a draft), users newly mentioned as @name are notified (unless either has blocked the other), once: a user already notified about the comment isn't notified again. Edits of any other comment, private messages included, notify no one.

The answer is JSON {"comment": <the new body rendered as HTML>}.

Refused, changing nothing: 400 for an empty body without a file, 403 for someone else's comment, 404 for an unknown comment, 401 for anonymous scripts. (Suspended users are refused; see the users area.)
'''
import os
import time

import pytest

from files.tests.spec.harness import *


def _edit(client, comment, body, headers=XHR, files=None):
	return client.post(f"/edit_comment/{comment['id']}", {"body": body}, headers=headers, files=files)


def _own(author=None, **overrides):
	author = author or factories.user()
	return author, factories.comment(author, factories.post(factories.user()), **overrides)


def _assert_answered(r, token):
	assert_status(r, 200)
	assert set(r.json) == {"comment"}, r.json
	assert token in r.json["comment"]


def test_editing_replaces_the_body():
	author, comment = _own()
	token = factories.unique()
	client = as_user(author)

	with db_diff() as d:
		r = _edit(client, comment, token)

	_assert_answered(r, token)
	d.assert_exactly(updated={"comments": {comment["id"]: {"body": token, "body_html": ANY}}})
	assert token in db.row("comments", id=comment["id"])["body_html"]


def test_editing_a_comment_older_than_3_minutes_marks_it_edited():
	author, comment = _own(created_utc=int(time.time()) - 181)
	token = factories.unique()
	client = as_user(author)
	before = int(time.time())

	with db_diff() as d:
		r = _edit(client, comment, token)

	_assert_answered(r, token)
	d.assert_exactly(updated={"comments": {comment["id"]: {"body": token, "body_html": ANY, "edited_utc": ANY}}})
	assert db.row("comments", id=comment["id"])["edited_utc"] >= before


def test_the_body_is_trimmed():
	author, comment = _own()
	token = factories.unique()

	assert_status(_edit(as_user(author), comment, f"  \n {token} \n "), 200)

	assert db.row("comments", id=comment["id"])["body"] == token


def test_an_unchanged_body_changes_nothing():
	author, comment = _own(created_utc=int(time.time()) - 600)
	client = as_user(author)

	with db_diff() as d:
		r = _edit(client, comment, comment["body"])

	_assert_answered(r, comment["body"])
	d.assert_exactly()


@pytest.mark.parametrize("state", ["REMOVED", "FILTERED"])
def test_hidden_comments_can_be_edited_without_notifying(state):
	author, comment = _own(state_mod=state)
	mentioned = factories.user()
	token = factories.unique()
	client = as_user(author)

	with db_diff() as d:
		r = _edit(client, comment, f"{token} @{mentioned['username']}")

	_assert_answered(r, token)
	d.assert_exactly(updated={"comments": {comment["id"]: {"body": ANY, "body_html": ANY}}})


# Mentions

def test_new_mentions_are_notified_once():
	author, comment = _own()
	mentioned = factories.user()
	client = as_user(author)

	with db_diff() as d:
		r = _edit(client, comment, f"{factories.unique()} @{mentioned['username']} @{mentioned['username']}")

	assert_status(r, 200)
	d.assert_exactly(
		inserted={"notifications": [{"user_id": mentioned["id"], "comment_id": comment["id"], "read": False}]},
		updated={"comments": {comment["id"]: {"body": ANY, "body_html": ANY}}},
	)


def test_users_already_notified_about_the_comment_arent_notified_again():
	author, comment = _own()
	mentioned = factories.user()
	db.insert("notifications", user_id=mentioned["id"], comment_id=comment["id"], read=True)
	client = as_user(author)

	with db_diff() as d:
		r = _edit(client, comment, f"{factories.unique()} @{mentioned['username']}")

	assert_status(r, 200)
	d.assert_exactly(updated={"comments": {comment["id"]: {"body": ANY, "body_html": ANY}}})


@pytest.mark.parametrize("case", ["self", "blocks the author", "blocked by the author"])
def test_some_mentions_notify_no_one(case):
	author, comment = _own()
	other = factories.user()
	if case == "blocks the author":
		db.insert("userblocks", user_id=other["id"], target_id=author["id"])
	if case == "blocked by the author":
		db.insert("userblocks", user_id=author["id"], target_id=other["id"])
	name = author["username"] if case == "self" else other["username"]
	client = as_user(author)

	with db_diff() as d:
		r = _edit(client, comment, f"{factories.unique()} @{name}")

	assert_status(r, 200)
	d.assert_exactly(updated={"comments": {comment["id"]: {"body": ANY, "body_html": ANY}}})


# Uploads

def _message(author):
	message_id = db.execute("SELECT nextval('comments_id_seq')")
	return db.insert("comments", id=message_id, author_id=author["id"], sentto=factories.user()["id"], created_utc=int(time.time()), parent_submission=None, level=1, top_comment_id=message_id, body="hi", body_html="<p>hi</p>", volunteer_janitor_badness=0.5, state_mod="VISIBLE", state_report="UNREPORTED")


UNPUBLISHED = {
	"deleted": lambda: _own(state_user_deleted_utc="2020-01-01T00:00:00Z"),
	"by a shadowbanned author": lambda: _own(author=factories.user(shadowbanned="somemod")),
	"on a draft": lambda: (lambda author: (author, factories.comment(author, factories.post(author, private=True))))(factories.user()),
	"a private message": lambda: (lambda author: (author, _message(author)))(factories.user()),
}


@pytest.mark.parametrize("case", UNPUBLISHED)
def test_edits_of_unpublished_comments_notify_no_one(case):
	author, comment = UNPUBLISHED[case]()
	mentioned = factories.user()
	client = as_user(author)

	with db_diff() as d:
		r = _edit(client, comment, f"{factories.unique()} @{mentioned['username']}")

	assert_status(r, 200)
	d.assert_exactly(updated={"comments": {comment["id"]: {"body": ANY, "body_html": ANY}}})


def _stored_images():
	return sorted(os.listdir(config.images_dir()))


def test_uploads_through_tor_are_dropped_but_the_text_saved():
	author, comment = _own()
	token = factories.unique()
	client = as_user(author)

	with db_diff() as d:
		r = _edit(client, comment, token, headers={**XHR, **TOR}, files={"file": uploads.png(2, 2)})

	_assert_answered(r, token)
	d.assert_exactly(updated={"comments": {comment["id"]: {"body": token, "body_html": ANY}}})
	assert _stored_images() == []


# Refusals

@pytest.mark.parametrize("body", ["", "   \n "])
def test_empty_bodies_are_refused(body):
	author, comment = _own()
	client = as_user(author)

	with db_diff() as d:
		r = _edit(client, comment, body)

	assert_status(r, 400)
	d.assert_exactly()


@pytest.mark.parametrize("editor", ["user", "admin"])
def test_someone_elses_comment_cant_be_edited(editor):
	_, comment = _own()
	client = as_user(factories.user() if editor == "user" else factories.admin(3))

	with db_diff() as d:
		r = _edit(client, comment, factories.unique())

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("which", ["unknown", "not an id"])
def test_unknown_comments_are_not_found(which):
	cid = db.execute("SELECT nextval('comments_id_seq')") if which == "unknown" else "abc"

	r = _edit(as_user(factories.user()), {"id": cid}, factories.unique())

	assert_status(r, 404)


def test_anonymous_scripts_are_unauthorized():
	_, comment = _own()

	with db_diff() as d:
		r = _edit(anon(), comment, factories.unique())

	assert_api_unauthorized(r)
	d.assert_exactly()
