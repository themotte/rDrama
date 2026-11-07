'''
GET /comment/<id> of a message is its conversation's page: the message and everything answering it, at any depth, oldest first, with no post around them. "context" (0 to 8, 0 by default) also shows that many of the messages it answers, above it. Who may open a message: its sender and recipient, those taking part in its conversation (test_replies: in modmail, its starter and admins from level 2), and admins from level 2; others are refused (403, see comments/test_permalink). A message isn't found under any post's path (/post/<post id>/<anything>/<id>): 404.

API clients get the shown conversation as JSON: its first shown message, with its replies.

"read" marks the viewer's notification of the message read.
'''
import pytest

from files.tests.spec.harness import *


def _conversation(length):
	sender, recipient = factories.user(), factories.user()
	chain = [factories.message(sender, recipient, created_utc=1000)]
	for i in range(length - 1):
		author, to = (recipient, sender) if i % 2 == 0 else (sender, recipient)
		chain.append(factories.message(author, to, chain[-1], created_utc=1001 + i))
	return sender, recipient, chain


@pytest.mark.parametrize("viewer", ["sender", "recipient"])
def test_shows_the_conversation_from_the_message_down(viewer):
	sender, recipient, chain = _conversation(3)

	r = as_user(sender if viewer == "sender" else recipient).get(f"/comment/{chain[1]['id']}")

	assert_html(r, 200)
	assert_in_order(r, [chain[1]["text"], chain[2]["text"]])
	assert_not_in_payload(r, chain[0]["text"])


def test_context_shows_the_messages_it_answers():
	sender, _, chain = _conversation(4)

	r = as_user(sender).get(f"/comment/{chain[3]['id']}", params={"context": 2})

	assert_in_order(r, [chain[1]["text"], chain[2]["text"], chain[3]["text"]])
	assert_not_in_payload(r, chain[0]["text"])


def test_long_conversations_show_whole():
	sender, _, chain = _conversation(14)

	r = as_user(sender).get(f"/comment/{chain[0]['id']}")

	assert_in_order(r, [message["text"] for message in chain])


def test_answers_show_oldest_first():
	sender, recipient = factories.user(), factories.user()
	message = factories.message(sender, recipient)
	later = factories.message(recipient, sender, message, created_utc=message["created_utc"] + 2)
	earlier = factories.message(sender, recipient, message, created_utc=message["created_utc"] + 1)

	assert_in_order(as_user(sender).get(f"/comment/{message['id']}"), [message["text"], earlier["text"], later["text"]])


@pytest.mark.parametrize("level", [2, 3])
def test_admins_from_level_2_open_other_users_messages(level):
	_, _, chain = _conversation(2)

	r = as_user(factories.admin(level)).get(f"/comment/{chain[0]['id']}")

	assert_html(r, 200)
	assert_in_payload(r, chain[1]["text"])


def test_level_1_admins_cant_open_other_users_messages():
	_, _, chain = _conversation(1)

	assert_status(as_user(factories.admin(1)).get(f"/comment/{chain[0]['id']}"), 403)


def test_messages_are_not_found_under_a_post():
	sender, recipient = factories.user(), factories.user()
	message = factories.message(sender, recipient)
	post = factories.post(factories.user())

	assert_status(as_user(sender).get(f"/post/{post['id']}/anything/{message['id']}"), 404)


def test_api_clients_get_the_conversation():
	sender, _, chain = _conversation(3)

	r = as_api(factories.api_token(sender)).get(f"/comment/{chain[1]['id']}")

	assert_status(r, 200)
	assert r.json["id"] == chain[1]["id"]
	assert [reply["id"] for reply in r.json["replies"]] == [chain[2]["id"]]


def test_read_marks_the_notification_read():
	sender, recipient = factories.user(), factories.user()
	message = factories.message(sender, recipient)
	factories.notification(recipient, message)
	client = as_user(recipient)

	with db_diff() as d:
		r = client.get(f"/comment/{message['id']}", params={"read": "1"})

	assert_html(r, 200)
	d.assert_exactly(updated={"notifications": {(recipient["id"], message["id"]): {"read": True}}})


def test_the_starter_opens_the_admins_answers_in_modmail():
	starter = factories.user()
	message = factories.message(starter, seed.MODMAIL_ID)
	answer = factories.message(factories.admin(3), seed.MODMAIL_ID, message)

	r = as_user(starter).get(f"/comment/{answer['id']}")

	assert_html(r, 200)
	assert_in_payload(r, answer["text"])


def test_others_cant_open_modmail():
	message = factories.message(factories.user(), seed.MODMAIL_ID)
	answer = factories.message(factories.admin(3), seed.MODMAIL_ID, message)

	assert_status(as_user(factories.user()).get(f"/comment/{answer['id']}"), 403)
