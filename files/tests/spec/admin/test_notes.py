'''
Admin notes about users, kept by admins of level 2 and up:
- POST /@<username>/create_note takes one form field, "data": a JSON object with "note" (the text), "tag" (a number, as a string or a number: 0 Quality, 1 Good, 2 Comment, 3 Warning, 4 Tempban, 5 Permban, 6 Spam, 7 Bot) and optionally "post" or "comment" (the id of the item the note is about; a comment wins over a post). It answers 200 with JSON {"success", "message", "note"}: on success "note" is the saved note, with "id", "author_name", "created" (unix seconds), "reference" (an absolute link to the item, or null), "note" and "tag" (the number); for an unknown user "success" is false and "note" null. Missing or malformed data, an unknown tag, a note over 10000 characters, or a post or comment that doesn't exist is refused with 400.
- POST /@<username>/delete_note/<id> deletes a note about that user, answering 200 with JSON whose "success" is true; any other id is 404.

The username is matched as profiles match it: case-insensitively, current or original name.

Post pages and post listings carry every note about each author shown, for viewers of admin level 2 and up only.
'''
import json
from urllib.parse import urlsplit

import pytest

from files.tests.spec.harness import *

TAGS = ["Quality", "Good", "Comment", "Warning", "Tempban", "Permban", "Spam", "Bot"]


def _create(client, username, data):
	return client.post(f"/@{username}/create_note", {"data": json.dumps(data)}, headers=XHR)


@pytest.mark.parametrize("tag", range(len(TAGS)), ids=TAGS)
def test_admin_notes_a_user(tag):
	admin, user = factories.admin(2), factories.user()
	text = factories.unique("note")
	client = as_user(admin)

	with db_diff() as d:
		r = _create(client, user["username"], {"note": text, "tag": str(tag), "post": None, "comment": None, "user": user["id"]})

	assert_status(r, 200)
	d.assert_exactly(inserted={"usernotes": [{"author_id": admin["id"], "reference_user": user["id"], "reference_post": None, "reference_comment": None, "note": text, "tag": TAGS[tag]}]})
	note_id = d.inserted["usernotes"][0]["id"]
	assert set(r.json) == {"success", "message", "note"} and r.json["success"] is True and isinstance(r.json["message"], str), r.json
	note = r.json["note"]
	assert (note["id"], note["author_name"], note["note"], note["tag"], note["reference"]) == (note_id, admin["username"], text, tag, None), note
	assert isinstance(note["created"], int), note


def test_a_note_about_a_post_links_to_the_post():
	admin, user = factories.admin(2), factories.user()
	post = factories.post(user)
	client = as_user(admin)

	with db_diff() as d:
		r = _create(client, user["username"], {"note": factories.unique("note"), "tag": 3, "post": post["id"]})

	assert_status(r, 200)
	d.assert_exactly(inserted={"usernotes": [{"reference_user": user["id"], "reference_post": post["id"], "reference_comment": None}]})
	assert r.json["note"]["reference"].startswith(f"{config.site_url()}/post/{post['id']}/"), r.json


def test_a_note_about_a_comment_links_to_the_comment_even_when_a_post_is_given_too():
	admin, user = factories.admin(2), factories.user()
	post = factories.post(user)
	comment = factories.comment(user, post)
	client = as_user(admin)

	with db_diff() as d:
		r = _create(client, user["username"], {"note": factories.unique("note"), "tag": 3, "post": post["id"], "comment": comment["id"]})

	assert_status(r, 200)
	d.assert_exactly(inserted={"usernotes": [{"reference_user": user["id"], "reference_post": None, "reference_comment": comment["id"]}]})
	reference = r.json["note"]["reference"]
	assert reference.startswith(f"{config.site_url()}/post/{post['id']}/") and urlsplit(reference).path.endswith(f"/{comment['id']}"), reference


def test_a_note_about_an_unknown_user_is_not_saved():
	client = as_user(factories.admin(2))

	with db_diff() as d:
		r = _create(client, factories.unique("nobody"), {"note": factories.unique("note"), "tag": 2})

	assert_status(r, 200)
	d.assert_exactly()
	assert set(r.json) == {"success", "message", "note"} and r.json["success"] is False and r.json["note"] is None and isinstance(r.json["message"], str), r.json


def test_admin_deletes_a_note():
	admin, user = factories.admin(2), factories.user()
	note = db.insert("usernotes", author_id=admin["id"], reference_user=user["id"], note=factories.unique("note"), tag="Warning")
	client = as_user(admin)

	with db_diff() as d:
		r = client.post(f"/@{user['username']}/delete_note/{note['id']}", headers=XHR)

	assert_status(r, 200)
	d.assert_exactly(deleted={"usernotes": [note["id"]]})
	assert r.json["success"] is True, r.json


@pytest.mark.parametrize("name", ["upper case", "original"])
def test_notes_find_the_user_as_profiles_do(name):
	user = factories.user(username=factories.unique("now"), original_username=factories.unique("was"))
	username = user["username"].upper() if name == "upper case" else user["original_username"]
	text = factories.unique("note")
	client = as_user(factories.admin(2))

	with db_diff() as d:
		r = _create(client, username, {"note": text, "tag": "2"})

	assert_status(r, 200)
	d.assert_exactly(inserted={"usernotes": [{"reference_user": user["id"], "note": text}]})


@pytest.mark.parametrize("case", ["another user's", "unknown", "not an id"])
def test_deleting_a_note_not_about_the_user_is_not_found(case):
	admin, user, other = factories.admin(2), factories.user(), factories.user()
	note = db.insert("usernotes", author_id=admin["id"], reference_user=other["id"], note=factories.unique("note"), tag="Warning")
	note_id = {"another user's": note["id"], "unknown": note["id"] + 1000, "not an id": "first"}[case]
	client = as_user(admin)

	with db_diff() as d:
		r = client.post(f"/@{user['username']}/delete_note/{note_id}", headers=XHR)

	assert_status(r, 404)
	d.assert_exactly()


# Notes in pages

def _noted_post_author():
	'''A visible post whose author has a note; returns (post, note text).'''
	author = factories.user()
	text = factories.unique("note")
	db.insert("usernotes", author_id=factories.admin(2)["id"], reference_user=author["id"], note=text, tag="Comment")
	return factories.post(author), text


def _noted_commenter():
	'''A visible post with a comment whose author has a note; returns (post, note text).'''
	post = factories.post(factories.user())
	commenter = factories.user()
	text = factories.unique("note")
	db.insert("usernotes", author_id=factories.admin(2)["id"], reference_user=commenter["id"], note=text, tag="Comment")
	factories.comment(commenter, post)
	return post, text


PAGES = [
	("post page", _noted_post_author, lambda post: f"/post/{post['id']}"),
	("comment on a post page", _noted_commenter, lambda post: f"/post/{post['id']}"),
	("front page", _noted_post_author, lambda post: "/"),
]


@pytest.mark.parametrize("arrange, path", [p[1:] for p in PAGES], ids=[p[0] for p in PAGES])
def test_pages_carry_authors_notes_for_admins(arrange, path):
	post, text = arrange()

	r = as_user(factories.admin(2)).get(path(post))

	assert_html(r, 200)
	assert_in_payload(r, text)


@pytest.mark.parametrize("level", [0, 1])
@pytest.mark.parametrize("arrange, path", [p[1:] for p in PAGES], ids=[p[0] for p in PAGES])
def test_pages_carry_no_notes_below_admin_level_2(arrange, path, level):
	post, text = arrange()

	r = as_user(factories.admin(level)).get(path(post))

	assert_html(r, 200)
	assert_not_in_payload(r, text)


@pytest.mark.parametrize("data", [
	pytest.param(None, id="no data"),
	pytest.param("not json", id="not JSON"),
	pytest.param(json.dumps(["a list"]), id="not an object"),
	pytest.param(json.dumps({"tag": "1"}), id="no note"),
	pytest.param(json.dumps({"note": "text"}), id="no tag"),
	pytest.param(json.dumps({"note": "text", "tag": "8"}), id="unknown tag"),
	pytest.param('{"note": "text", "tag": Infinity}', id="infinite tag"),
	pytest.param(json.dumps({"note": "x" * 10001, "tag": "1"}), id="note over 10000 characters"),
	pytest.param(json.dumps({"note": "text", "tag": "Good"}), id="tag by name"),
	pytest.param(json.dumps({"note": 5, "tag": "1"}), id="note not text"),
	pytest.param(json.dumps({"note": "text", "tag": "1", "post": "{unknown}"}), id="unknown post"),
	pytest.param(json.dumps({"note": "text", "tag": "1", "comment": "{unknown}"}), id="unknown comment"),
	pytest.param(json.dumps({"note": "text", "tag": "1", "post": "first"}), id="post not an id"),
])
def test_a_malformed_note_is_refused(data):
	user = factories.user()
	unknown = db.execute("SELECT nextval('submissions_id_seq')") + 1000
	client = as_user(factories.admin(2))
	form = {} if data is None else {"data": data.replace("{unknown}", str(unknown))}

	with db_diff() as d:
		r = client.post(f"/@{user['username']}/create_note", form, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()
