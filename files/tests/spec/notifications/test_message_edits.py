'''
Editing a message (POST /edit_comment/<id> by its sender, as comments are edited: comments/test_edit) keeps it within what messages may be: its text is cut to 10000 characters, as when sending it, so it is never long enough to be held for review.
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
