'''
POST /@<username>/message, with "message": a logged-in user sends a private message to the user with that username (or former username, in any letter case; 404 when there's none).

The message is a comment with no post, sent to the recipient: the first of a new conversation (its own top). Its text is rendered from "message", which is trimmed and cut to 10000 characters; its source isn't kept. The recipient is notified. The reply is {"message": ...}.

Refused:
- an empty (or all-whitespace) message: 400;
- yourself: 400;
- modmail's account and the site's other system accounts: 403 (the admins are reached through /contact);
- suspended senders, temporarily or permanently: 403 (they can still write to modmail);
- users the sender blocks, and users who block the sender, unless the sender is an admin from level 2: 403;
- senders who aren't yet part of the community (no visible post or comment, and no admin level), unless the recipient is an admin from level 2: 403;
- the same text again to the same user (any earlier message from the sender to them that reads the same): 403.

Messaging by API token works as by session.
'''
import time

import pytest

from files.tests.spec.harness import *


def _sender(**overrides):
	'''A user who may send messages: they have a visible post.'''
	user = factories.user(**overrides)
	factories.post(user)
	return user


def _send(sender, recipient, text, **kwargs):
	return as_user(sender).post(f"/@{recipient['username']}/message", {"message": text}, headers=XHR, **kwargs)


def test_logged_out_visitors_are_refused():
	assert_api_unauthorized(anon().post(f"/@{factories.user()['username']}/message", {"message": "hi"}, headers=XHR))


def test_sends_a_message_and_notifies_the_recipient():
	sender, recipient = _sender(), factories.user()
	text = factories.unique("message")

	with db_diff() as d:
		r = _send(sender, recipient, text)

	assert_json_message(r)
	message = d.inserted["comments"][0]["id"] if d.inserted.get("comments") else None
	d.assert_exactly(inserted={
		"comments": [{"id": message, "author_id": sender["id"], "sentto": recipient["id"], "parent_submission": None, "parent_comment_id": None, "level": 1, "top_comment_id": message, "body": None, "state_mod": "VISIBLE"}],
		"notifications": [{"user_id": recipient["id"], "comment_id": message, "read": False}],
	})
	assert text in db.row("comments", id=message)["body_html"]


def test_the_recipient_is_found_by_former_username_in_any_case():
	sender, recipient = _sender(), factories.user()
	db.update("users", {"id": recipient["id"]}, username=factories.unique("renamed"))

	assert_json_message(as_user(sender).post(f"/@{recipient['original_username'].upper()}/message", {"message": factories.unique()}, headers=XHR))

	assert db.row("comments", author_id=sender["id"], parent_submission=None)["sentto"] == recipient["id"]


def test_through_the_api():
	sender, recipient = _sender(), factories.user()

	assert_json_message(as_api(factories.api_token(sender)).post(f"/@{recipient['username']}/message", {"message": factories.unique()}))

	assert db.row("comments", author_id=sender["id"], parent_submission=None)["sentto"] == recipient["id"]


def test_an_unknown_recipient_is_not_found():
	assert_status(as_user(_sender()).post(f"/@{factories.unique('nobody')}/message", {"message": "hi"}, headers=XHR), 404)


def test_the_text_is_trimmed_and_cut_to_10000_characters():
	sender, recipient = _sender(), factories.user()
	kept, cut = factories.unique("kept"), factories.unique("cut")
	text = kept + "a" * (10000 - len(kept)) + cut

	assert_json_message(_send(sender, recipient, f"   {text}   "))

	body_html = db.row("comments", author_id=sender["id"], parent_submission=None)["body_html"]
	assert kept in body_html and cut not in body_html


@pytest.mark.parametrize("text", ["", "   "], ids=["empty", "whitespace"])
def test_empty_messages_are_refused(text):
	sender, recipient = _sender(), factories.user()

	with db_diff() as d:
		r = _send(sender, recipient, text)

	assert_status(r, 400)
	d.assert_exactly()


def _refused(sender, recipient, status=403):
	with db_diff() as d:
		r = _send(sender, recipient, factories.unique())
	assert_status(r, status)
	d.assert_exactly()


@pytest.mark.parametrize("account", [seed.SYSTEM_ID, seed.MODMAIL_ID], ids=["system", "modmail"])
def test_system_accounts_are_refused(account):
	_refused(_sender(), db.row("users", id=account))


def test_messaging_yourself_is_refused():
	sender = _sender()

	_refused(sender, sender, 400)


@pytest.mark.parametrize("ban", ["permanent", "temporary"])
def test_suspended_senders_are_refused(ban):
	_refused(_sender(is_banned=seed.AUTOJANNY_ID, unban_utc=0 if ban == "permanent" else int(time.time()) + 86400), factories.user())


def test_a_ban_that_ran_out_doesnt_stop_messages():
	assert_json_message(_send(_sender(is_banned=seed.AUTOJANNY_ID, unban_utc=int(time.time()) - 60), factories.user(), factories.unique()))


def test_messaging_a_user_you_block_is_refused():
	sender, recipient = _sender(), factories.user()
	db.insert("userblocks", user_id=sender["id"], target_id=recipient["id"])

	_refused(sender, recipient)


@pytest.mark.parametrize("level", [0, 1])
def test_messaging_a_user_who_blocks_you_is_refused(level):
	sender, recipient = _sender(admin_level=level), factories.user()
	db.insert("userblocks", user_id=recipient["id"], target_id=sender["id"])

	_refused(sender, recipient)


@pytest.mark.parametrize("level", [2, 3])
def test_admins_message_users_who_block_them(level):
	sender, recipient = factories.admin(level), factories.user()
	db.insert("userblocks", user_id=recipient["id"], target_id=sender["id"])

	assert_json_message(_send(sender, recipient, factories.unique()))


def test_newcomers_are_refused():
	_refused(factories.user(), factories.user())


@pytest.mark.parametrize("contribution", ["post", "comment"])
def test_a_visible_post_or_comment_makes_a_newcomer_part_of_the_community(contribution):
	sender = factories.user()
	post = factories.post(factories.user())
	factories.post(sender) if contribution == "post" else factories.comment(sender, post)

	assert_json_message(_send(sender, factories.user(), factories.unique()))


@pytest.mark.parametrize("state", [{"state_mod": "REMOVED"}, {"state_mod": "FILTERED"}, {"state_user_deleted_utc": "2020-01-01T00:00:00Z"}], ids=["removed", "filtered", "deleted"])
def test_hidden_posts_dont_count_as_contributions(state):
	sender = factories.user()
	factories.post(sender, **state)

	_refused(sender, factories.user())


def test_admins_are_part_of_the_community():
	assert_json_message(_send(factories.admin(1), factories.user(), factories.unique()))


@pytest.mark.parametrize("level", [2, 3])
def test_newcomers_may_message_admins_from_level_2(level):
	assert_json_message(_send(factories.user(), factories.admin(level), factories.unique()))


def test_newcomers_may_not_message_level_1_admins():
	_refused(factories.user(), factories.admin(1))


def test_the_same_text_to_the_same_user_is_refused():
	sender, recipient = _sender(), factories.user()
	text = factories.unique()
	assert_json_message(_send(sender, recipient, text))

	_refused_text(sender, recipient, text)


def _refused_text(sender, recipient, text):
	with db_diff() as d:
		r = _send(sender, recipient, text)
	assert_status(r, 403)
	d.assert_exactly()


def test_the_same_text_is_refused_however_many_times_it_was_sent():
	sender, recipient = _sender(), factories.user()
	text = factories.unique()
	assert_json_message(_send(sender, recipient, text))
	message = db.row("comments", author_id=sender["id"], parent_submission=None)
	assert_status(as_user(sender).post("/reply", {"parent_id": message["id"], "body": text}, headers=XHR), 200)

	_refused_text(sender, recipient, text)


def test_the_same_text_to_someone_else_is_sent():
	sender = _sender()
	text = factories.unique()
	assert_json_message(_send(sender, factories.user(), text))

	assert_json_message(_send(sender, factories.user(), text))


def test_a_factory_message_matches_a_sent_one():
	sender, recipient = _sender(), factories.user()
	_send(sender, recipient, factories.unique())
	sent = db.row("comments", author_id=sender["id"], parent_submission=None)
	arranged = factories.message(_sender(), recipient)

	ignored = {"id", "top_comment_id", "author_id", "body_html", "created_utc", "text"}
	assert {k: v for k, v in sent.items() if k not in ignored} == {k: v for k, v in arranged.items() if k not in ignored}
	assert sent["top_comment_id"] == sent["id"] and arranged["top_comment_id"] == arranged["id"]
	assert db.rows("commentvotes", comment_id=sent["id"]) == []
