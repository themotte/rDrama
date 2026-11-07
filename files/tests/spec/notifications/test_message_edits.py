'''
Editing a message (POST /edit_comment/<id> by its sender, as comments are edited: comments/test_edit) keeps it within what messages may be: its text is cut to 10000 characters, as when sending it, so it is never long enough to be held for review. Images can be uploaded with an edit (and are linked after the text, as in comment edits) only in modmail threads, as when replying; elsewhere an upload is refused (400). Uploads through Tor are ignored.
'''
from files.tests.spec.harness import *


def _edit(user, message, body, **kwargs):
	return as_user(user).post(f"/edit_comment/{message['id']}", {"body": body}, headers=XHR, **kwargs)


def test_an_edit_is_cut_to_10000_characters():
	sender = factories.user()
	message = factories.message(sender, factories.user())
	kept, cut = factories.unique("kept"), factories.unique("cut")

	assert_status(_edit(sender, message, kept + "a" * (10000 - len(kept)) + cut), 200)

	edited = db.row("comments", id=message["id"])
	assert kept in edited["body_html"] and cut not in edited["body_html"]
	assert len(edited["body"]) == 10000


def test_a_long_edit_isnt_held_for_review():
	sender = factories.user()
	message = factories.message(sender, factories.user())

	assert_status(_edit(sender, message, "word " * 12000), 200)

	assert db.row("comments", id=message["id"])["state_mod"] == "VISIBLE"


def test_an_edit_in_a_direct_thread_cant_upload_images():
	sender = factories.user()
	message = factories.message(sender, factories.user())
	client = as_user(sender)

	with db_diff() as d:
		r = client.post(f"/edit_comment/{message['id']}", {"body": factories.unique()}, headers=XHR, files={"file": uploads.png(4, 4)})

	assert_status(r, 400)
	d.assert_exactly()


def test_an_edit_in_modmail_uploads_images():
	starter = factories.user()
	message = factories.message(starter, seed.MODMAIL_ID)

	assert_status(_edit(starter, message, factories.unique(), files={"file": uploads.png(4, 4)}), 200)

	assert "/images/" in db.row("comments", id=message["id"])["body_html"]
