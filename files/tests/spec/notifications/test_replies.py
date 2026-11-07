'''
POST /reply, with "parent_id" and "body": a logged-in user answers a message in a conversation they take part in.

In a conversation between two users (a direct thread), the reply is a message to the other one, under the message it answers, in the same thread (`top_comment_id`), one level deeper. Its text is rendered from "body", trimmed and cut to 10000 characters; its source isn't kept. The other user is notified.

Without "parent_id" the reply is refused (400); one that names no message is not found (404).

Replying doesn't need the sender to be part of the community, unlike starting a conversation (test_messages).

The reply is {"comment": ...}: the new message rendered for the page.
'''
import pytest

from files.tests.spec.harness import *


def _reply(user, parent, text, **kwargs):
	return as_user(user).post("/reply", {"parent_id": parent["id"], "body": text}, headers=XHR, **kwargs)


def _replied(d, author, recipient, parent):
	reply = d.inserted["comments"][0]["id"] if d.inserted.get("comments") else None
	d.assert_exactly(inserted={
		"comments": [{"id": reply, "author_id": author["id"], "sentto": recipient["id"], "parent_submission": None, "parent_comment_id": parent["id"], "level": parent["level"] + 1, "top_comment_id": parent["top_comment_id"], "body": None, "state_mod": "VISIBLE"}],
		"notifications": [{"user_id": recipient["id"], "comment_id": reply, "read": False}],
	})
	return reply


def test_logged_out_visitors_are_refused():
	message = factories.message(factories.user(), factories.user())

	assert_api_unauthorized(anon().post("/reply", {"parent_id": message["id"], "body": "hi"}, headers=XHR))


def test_a_missing_parent_is_refused():
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.post("/reply", {"body": factories.unique()}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


@pytest.mark.parametrize("parent_id", ["x", "99999999"], ids=["garbled", "unknown"])
def test_an_unknown_parent_is_not_found(parent_id):
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.post("/reply", {"parent_id": parent_id, "body": factories.unique()}, headers=XHR)

	assert_status(r, 404)
	d.assert_exactly()


def test_the_recipient_answers_the_sender():
	sender, recipient = factories.user(), factories.user()
	message = factories.message(sender, recipient)
	text = factories.unique("reply")

	with db_diff() as d:
		r = _reply(recipient, message, text)

	assert_status(r, 200)
	assert_in_payload(r, text)
	reply = _replied(d, recipient, sender, message)
	assert text in db.row("comments", id=reply)["body_html"]


def test_the_sender_follows_up_their_own_message():
	sender, recipient = factories.user(), factories.user()
	message = factories.message(sender, recipient)

	with db_diff() as d:
		r = _reply(sender, message, factories.unique())

	assert_status(r, 200)
	_replied(d, sender, recipient, message)


def test_answers_deep_in_the_conversation_go_to_the_other_user():
	sender, recipient = factories.user(), factories.user()
	message = factories.message(sender, recipient)
	answer = factories.message(recipient, sender, message)

	with db_diff() as d:
		r = _reply(sender, answer, factories.unique())

	assert_status(r, 200)
	_replied(d, sender, recipient, answer)


def test_newcomers_may_reply():
	sender, newcomer = factories.user(), factories.user()
	factories.post(sender)
	message = factories.message(sender, newcomer)

	with db_diff() as d:
		r = _reply(newcomer, message, factories.unique())

	assert_status(r, 200)
	_replied(d, newcomer, sender, message)


def test_through_the_api():
	sender, recipient = factories.user(), factories.user()
	message = factories.message(sender, recipient)

	r = as_api(factories.api_token(recipient)).post("/reply", {"parent_id": message["id"], "body": factories.unique()})

	assert_status(r, 200)
	assert db.row("comments", author_id=recipient["id"], parent_comment_id=message["id"])["sentto"] == sender["id"]


def test_the_text_is_trimmed_and_cut_to_10000_characters():
	sender, recipient = factories.user(), factories.user()
	message = factories.message(sender, recipient)
	kept, cut = factories.unique("kept"), factories.unique("cut")

	assert_status(_reply(recipient, message, f"  {kept}{'a' * (10000 - len(kept))}{cut}  "), 200)

	body_html = db.row("comments", author_id=recipient["id"], parent_comment_id=message["id"])["body_html"]
	assert kept in body_html and cut not in body_html


def test_empty_replies_are_refused():
	sender, recipient = factories.user(), factories.user()
	message = factories.message(sender, recipient)

	with db_diff() as d:
		r = _reply(recipient, message, "   ")

	assert_status(r, 400)
	d.assert_exactly()


def test_a_factory_reply_matches_one_sent_through_the_site():
	sender, recipient = factories.user(), factories.user()
	message = factories.message(sender, recipient)
	_reply(recipient, message, factories.unique())
	sent = db.row("comments", author_id=recipient["id"], parent_comment_id=message["id"])
	arranged = factories.message(recipient, sender, message)

	ignored = {"id", "body_html", "created_utc", "text"}
	assert {k: v for k, v in sent.items() if k not in ignored} == {k: v for k, v in arranged.items() if k not in ignored}


# Modmail

def test_replying_to_an_admins_modmail_reply_notifies_each_admin_once():
	starter, admin = factories.user(), factories.admin(3)
	message = factories.message(starter, seed.MODMAIL_ID)
	answer = factories.message(admin, None, message)

	r = _reply(starter, answer, factories.unique())

	assert_status(r, 200)
	reply = db.row("comments", author_id=starter["id"], parent_comment_id=answer["id"])
	assert [n["user_id"] for n in db.rows("notifications", comment_id=reply["id"])] == [admin["id"]]
