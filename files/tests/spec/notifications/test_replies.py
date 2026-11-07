'''
POST /reply, with "parent_id" and "body": a logged-in user answers a message in a conversation they take part in.

In a conversation between two users (a direct thread), the reply is a message to the other one, under the message it answers, in the same thread (`top_comment_id`), one level deeper. Its text is rendered from "body", trimmed and cut to 10000 characters; its source isn't kept. The other user is notified.

Without "parent_id" the reply is refused (400); one that names no message is not found (404).

Only messages in a conversation can be answered, by those taking part in it: in a direct thread, its two users; in a modmail thread (one started by a message to modmail), its starter and admins from level 2. API tokens act as admin level 0, so an admin's API client takes part in modmail only in threads its user started. Refused (403): replies to comments on posts, to the site's notices, to messages older versions left outside any conversation, and to conversations the replier doesn't take part in, other users' included even for admins.

Replying doesn't need the sender to be part of the community, unlike starting a conversation (test_messages).

In a modmail thread, every reply is a message to modmail, in the same thread. The admins from level 2 other than the replier are notified, each once; when an admin replies, so is the thread's starter, unless the starter is the site itself (a visitor's message from the contact form, or a notice).

In a direct thread, replying to a user you block, or who blocks you (unless you're an admin from level 2), is refused (403), as starting a conversation is. Blocks don't apply in modmail.

Suspended users (temporarily or permanently) can't reply (403), except in modmail threads they started, so they can still appeal; a suspended admin can't answer other users' modmail.

An image "file" can be attached anywhere in a modmail thread; files from Tor are ignored, and a file that isn't an image is refused (400). Elsewhere a file is refused (400).

The reply is {"comment": ...}: the new message rendered for the page.
'''
import re
import time

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


def _refused(user, parent):
	client = as_user(user)
	with db_diff() as d:
		r = client.post("/reply", {"parent_id": parent["id"], "body": factories.unique()}, headers=XHR)
	assert_status(r, 403)
	d.assert_exactly()


def test_comments_on_posts_cant_be_answered_privately():
	comment = factories.comment(factories.user(), factories.post(factories.user()))

	_refused(factories.user(), comment)


def test_notices_cant_be_answered():
	user = factories.user()
	for author in (seed.SYSTEM_ID, seed.AUTOJANNY_ID):
		notice = factories.message(db.row("users", id=author), None, distinguish_level=6)
		factories.notification(user, notice)

		_refused(user, notice)


def test_messages_outside_any_conversation_cant_be_answered():
	comment = factories.comment(factories.user(), factories.post(factories.user()))
	user = factories.user()
	private_reply = factories.message(user, db.row("users", id=comment["author_id"]), parent=comment)

	_refused(db.row("users", id=comment["author_id"]), private_reply)
	_refused(user, private_reply)


def test_messages_whose_conversation_is_lost_cant_be_answered():
	'''Older versions left messages pointing at a first message that isn't one: here a reply in a modmail thread.'''
	starter, admin = factories.user(), factories.admin(3)
	answer = factories.message(admin, seed.MODMAIL_ID, factories.message(starter, seed.MODMAIL_ID))
	stray = factories.message(starter, admin, top_comment_id=answer["id"], level=1)

	_refused(admin, stray)
	_refused(starter, stray)


@pytest.mark.parametrize("top", ["missing", "none"])
def test_messages_whose_first_message_is_gone_cant_be_answered(top):
	sender, recipient = factories.user(), factories.user()
	stray = factories.message(sender, recipient, top_comment_id=None)
	if top == "missing": db.update("comments", {"id": stray["id"]}, top_comment_id=stray["id"] + 100000)

	_refused(recipient, stray)


@pytest.mark.parametrize("outsider", ["user", "level 2 admin", "level 3 admin"])
def test_outsiders_cant_answer_other_users_conversations(outsider):
	message = factories.message(factories.user(), factories.user())
	user = {"user": factories.user(), "level 2 admin": factories.admin(2), "level 3 admin": factories.admin(3)}[outsider]

	_refused(user, message)


def test_an_outsider_who_got_into_a_conversation_cant_answer_in_it():
	'''Older versions let anyone answer any message.'''
	sender, recipient, outsider = factories.user(), factories.user(), factories.user()
	message = factories.message(sender, recipient)
	intrusion = factories.message(outsider, sender, message)

	_refused(outsider, intrusion)


@pytest.mark.parametrize("outsider", ["user", "level 1 admin"])
def test_only_the_starter_and_admins_take_part_in_modmail(outsider):
	message = factories.message(factories.user(), seed.MODMAIL_ID)

	_refused(factories.user(admin_level=0 if outsider == "user" else 1), message)


def test_an_admins_api_client_takes_part_in_modmail_only_as_its_starter():
	admin = factories.admin(3)
	others = factories.message(factories.user(), seed.MODMAIL_ID)
	own = factories.message(admin, seed.MODMAIL_ID)
	client = as_api(factories.api_token(admin))

	with db_diff() as d:
		r = client.post("/reply", {"parent_id": others["id"], "body": factories.unique()})

	assert_status(r, 403)
	d.assert_exactly()
	assert_status(client.post("/reply", {"parent_id": own["id"], "body": factories.unique()}), 200)


@pytest.mark.parametrize("who", ["starter", "level 2 admin", "level 3 admin"])
def test_modmail_is_answered_by_its_starter_and_admins(who):
	starter = factories.user()
	message = factories.message(starter, seed.MODMAIL_ID)
	user = {"starter": starter, "level 2 admin": factories.admin(2), "level 3 admin": factories.admin(3)}[who]

	assert_status(_reply(user, message, factories.unique()), 200)


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

def _modmail_replied(d, author, parent, notified):
	reply = d.inserted["comments"][0]["id"] if d.inserted.get("comments") else None
	d.assert_exactly(inserted={
		"comments": [{"id": reply, "author_id": author["id"], "sentto": seed.MODMAIL_ID, "parent_submission": None, "parent_comment_id": parent["id"], "level": parent["level"] + 1, "top_comment_id": parent["top_comment_id"], "body": None, "state_mod": "VISIBLE"}],
		"notifications": [{"user_id": user["id"], "comment_id": reply, "read": False} for user in notified],
	})


@pytest.mark.parametrize("deep", [False, True], ids=["first message", "deeper"])
def test_the_starter_answers_the_admins(deep):
	starter, admins = factories.user(), [factories.admin(2), factories.admin(3)]
	parent = factories.message(starter, seed.MODMAIL_ID)
	if deep: parent = factories.message(admins[1], seed.MODMAIL_ID, parent)
	client = as_user(starter)

	with db_diff() as d:
		r = client.post("/reply", {"parent_id": parent["id"], "body": factories.unique()}, headers=XHR)

	assert_status(r, 200)
	_modmail_replied(d, starter, parent, admins)


@pytest.mark.parametrize("deep", [False, True], ids=["first message", "deeper"])
def test_an_admin_answers_the_starter_and_the_other_admins(deep):
	starter, admin, others = factories.user(), factories.admin(3), [factories.admin(2), factories.admin(3)]
	parent = factories.message(starter, seed.MODMAIL_ID)
	if deep: parent = factories.message(starter, seed.MODMAIL_ID, factories.message(others[1], seed.MODMAIL_ID, parent))
	client = as_user(admin)

	with db_diff() as d:
		r = client.post("/reply", {"parent_id": parent["id"], "body": factories.unique()}, headers=XHR)

	assert_status(r, 200)
	_modmail_replied(d, admin, parent, [starter, *others])


def test_answering_the_site_notifies_only_the_other_admins():
	admin, other = factories.admin(3), factories.admin(2)
	message = factories.message(db.row("users", id=seed.SYSTEM_ID), seed.MODMAIL_ID)
	client = as_user(admin)

	with db_diff() as d:
		r = client.post("/reply", {"parent_id": message["id"], "body": factories.unique()}, headers=XHR)

	assert_status(r, 200)
	_modmail_replied(d, admin, message, [other])


def test_an_admin_who_started_modmail_is_notified_once():
	starter, admin = factories.admin(3), factories.admin(3)
	message = factories.message(starter, seed.MODMAIL_ID)
	client = as_user(admin)

	with db_diff() as d:
		r = client.post("/reply", {"parent_id": message["id"], "body": factories.unique()}, headers=XHR)

	assert_status(r, 200)
	_modmail_replied(d, admin, message, [starter])


@pytest.mark.parametrize("sentto", ["nobody", "starter", "admin"])
def test_answers_older_versions_sent_elsewhere_are_still_modmail(sentto):
	'''Older versions sent admins' answers to no one, or to whoever they answered.'''
	starter, admin = factories.user(), factories.admin(3)
	message = factories.message(starter, seed.MODMAIL_ID)
	answer = factories.message(admin, {"nobody": None, "starter": starter, "admin": admin}[sentto], message)
	client = as_user(starter)

	with db_diff() as d:
		r = client.post("/reply", {"parent_id": answer["id"], "body": factories.unique()}, headers=XHR)

	assert_status(r, 200)
	_modmail_replied(d, starter, answer, [admin])


# Images

def _image_urls(body_html):
	return re.findall(r'<img[^>]* src="([^"]+)"', body_html)


@pytest.mark.parametrize("deep", [False, True], ids=["first message", "deeper"])
def test_images_are_attached_in_modmail(deep):
	starter, admin = factories.user(), factories.admin(3)
	parent = factories.message(starter, seed.MODMAIL_ID)
	if deep: parent = factories.message(admin, seed.MODMAIL_ID, parent)

	assert_status(_reply(starter, parent, factories.unique(), files={"file": uploads.png(4, 4)}), 200)

	urls = _image_urls(db.row("comments", author_id=starter["id"], parent_comment_id=parent["id"])["body_html"])
	assert len(urls) == 1
	assert_serves_image(urls[0])


def test_files_from_tor_are_ignored_in_modmail():
	starter = factories.user()
	message = factories.message(starter, seed.MODMAIL_ID)

	assert_status(as_user(starter).post("/reply", {"parent_id": message["id"], "body": factories.unique()}, headers={**XHR, **TOR}, files={"file": uploads.png(4, 4)}), 200)

	assert _image_urls(db.row("comments", author_id=starter["id"], parent_comment_id=message["id"])["body_html"]) == []


def test_files_from_tor_are_ignored_in_direct_threads():
	sender, recipient = factories.user(), factories.user()
	message = factories.message(sender, recipient)

	assert_status(as_user(recipient).post("/reply", {"parent_id": message["id"], "body": factories.unique()}, headers={**XHR, **TOR}, files={"file": uploads.png(4, 4)}), 200)


def test_files_that_arent_images_are_refused_in_modmail():
	starter = factories.user()
	message = factories.message(starter, seed.MODMAIL_ID)
	client = as_user(starter)

	with db_diff() as d:
		r = client.post("/reply", {"parent_id": message["id"], "body": factories.unique()}, headers=XHR, files={"file": ("notes.txt", b"hello", "text/plain")})

	assert_status(r, 400)
	d.assert_exactly()


def test_files_are_refused_in_direct_threads():
	sender, recipient = factories.user(), factories.user()
	message = factories.message(sender, recipient)
	client = as_user(recipient)

	with db_diff() as d:
		r = client.post("/reply", {"parent_id": message["id"], "body": factories.unique()}, headers=XHR, files={"file": uploads.png(4, 4)})

	assert_status(r, 400)
	d.assert_exactly()


# Suspension

def _suspended(ban, **overrides):
	return factories.user(is_banned=seed.AUTOJANNY_ID, unban_utc=0 if ban == "permanent" else int(time.time()) + 86400, **overrides)


@pytest.mark.parametrize("ban", ["permanent", "temporary"])
def test_suspended_users_cant_reply(ban):
	user = _suspended(ban)
	message = factories.message(factories.user(), user)

	_refused(user, message)


@pytest.mark.parametrize("ban", ["permanent", "temporary"])
def test_suspended_users_answer_their_own_modmail(ban):
	user = _suspended(ban)
	message = factories.message(user, seed.MODMAIL_ID)
	answer = factories.message(factories.admin(3), seed.MODMAIL_ID, message)

	assert_status(_reply(user, answer, factories.unique()), 200)


@pytest.mark.parametrize("ban", ["permanent", "temporary"])
def test_suspended_admins_cant_answer_others_modmail(ban):
	admin = _suspended(ban, admin_level=3)
	message = factories.message(factories.user(), seed.MODMAIL_ID)

	_refused(admin, message)


# Blocks

def test_replying_to_a_user_you_block_is_refused():
	sender, recipient = factories.user(), factories.user()
	message = factories.message(sender, recipient)
	db.insert("userblocks", user_id=recipient["id"], target_id=sender["id"])

	_refused(recipient, message)


@pytest.mark.parametrize("level", [0, 1])
def test_replying_to_a_user_who_blocks_you_is_refused(level):
	sender, recipient = factories.user(), factories.user(admin_level=level)
	message = factories.message(sender, recipient)
	db.insert("userblocks", user_id=sender["id"], target_id=recipient["id"])

	_refused(recipient, message)


@pytest.mark.parametrize("level", [2, 3])
def test_admins_reply_to_users_who_block_them(level):
	sender, admin = factories.user(), factories.admin(level)
	message = factories.message(sender, admin)
	db.insert("userblocks", user_id=sender["id"], target_id=admin["id"])

	assert_status(_reply(admin, message, factories.unique()), 200)


def test_blocks_dont_apply_in_modmail():
	starter, admin = factories.user(), factories.admin(3)
	message = factories.message(starter, seed.MODMAIL_ID)
	db.insert("userblocks", user_id=starter["id"], target_id=admin["id"])
	db.insert("userblocks", user_id=admin["id"], target_id=starter["id"])

	assert_status(_reply(admin, message, factories.unique()), 200)
	assert_status(_reply(starter, message, factories.unique()), 200)
