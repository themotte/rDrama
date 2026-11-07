'''
Modmail: messages to the site's admins, sent to the modmail account (`seed.MODMAIL_ID`).

GET /contact (also /press and /media) is the contact form, for everyone.

POST /send_admin, with "message" and optionally "email" and an image "file", sends it: a new conversation (a message that is its own top) from the logged-in user, or from the system account for visitors. Its text holds the message and the email given. An image is attached to it, except from Tor, where files are ignored; a file that isn't an image is refused (400). An empty message is refused (400). The admins who receive modmail (those from level 2) are notified, except the writer. The reply is the contact form again, saying the message was sent.

Requesting API keys (POST /api_keys) also writes modmail: a notice from the system account, of which the admins who receive modmail are notified.

GET /notifications/modmail lists modmail conversations (their first messages) for admins from level 2, newest first: 25 to a page, "page" (from 1) choosing it, each with its replies. Showing them marks the admin's notifications of their messages read. API clients and lower levels are refused (403); visitors are sent to log in.
'''
import re

import pytest

from files.tests.spec.harness import *


@pytest.mark.parametrize("path", ["/contact", "/press", "/media"])
@pytest.mark.parametrize("viewer", ["visitor", "user"])
def test_the_contact_form(path, viewer):
	client = anon() if viewer == "visitor" else as_user(factories.user())

	assert_html(client.get(path), 200)


@pytest.mark.parametrize("sender", ["user", "visitor"])
def test_sends_modmail_and_notifies_the_admins_who_receive_it(sender):
	user = factories.user()
	client = as_user(user) if sender == "user" else anon()
	receivers = [factories.admin(2), factories.admin(3)]
	factories.admin(1)
	text, email = factories.unique("message"), factories.unique("email")

	with db_diff() as d:
		r = client.post("/send_admin", {"message": text, "email": email})

	assert_html(r, 200)
	message = d.inserted["comments"][0]["id"] if d.inserted.get("comments") else None
	author = user["id"] if sender == "user" else seed.SYSTEM_ID
	d.assert_exactly(inserted={
		"comments": [{"id": message, "author_id": author, "sentto": seed.MODMAIL_ID, "parent_submission": None, "parent_comment_id": None, "level": 1, "top_comment_id": message, "state_mod": "VISIBLE"}],
		"notifications": [{"user_id": admin["id"], "comment_id": message, "read": False} for admin in receivers],
	})
	body_html = db.row("comments", id=message)["body_html"]
	assert text in body_html and email in body_html


def test_an_empty_message_is_refused():
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.post("/send_admin", {"message": ""})

	assert_status(r, 400)
	d.assert_exactly()


def _image_urls(body_html):
	return re.findall(r'<img[^>]* src="([^"]+)"', body_html)


def test_an_image_is_attached():
	user = factories.user()

	assert_html(as_user(user).post("/send_admin", {"message": factories.unique()}, files={"file": uploads.png(4, 4)}), 200)

	urls = _image_urls(db.row("comments", author_id=user["id"], sentto=seed.MODMAIL_ID)["body_html"])
	assert len(urls) == 1
	assert_serves_image(urls[0])


def test_files_from_tor_are_ignored():
	user = factories.user()

	assert_html(as_user(user).post("/send_admin", {"message": factories.unique()}, files={"file": uploads.png(4, 4)}, headers=TOR), 200)

	assert _image_urls(db.row("comments", author_id=user["id"], sentto=seed.MODMAIL_ID)["body_html"]) == []


def test_a_file_that_isnt_an_image_is_refused():
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.post("/send_admin", {"message": factories.unique()}, files={"file": ("notes.txt", b"hello", "text/plain")})

	assert_status(r, 400)
	d.assert_exactly()


def test_requesting_api_keys_notifies_the_admins_who_receive_modmail():
	receivers = [factories.admin(2), factories.admin(3)]
	factories.admin(1)
	client = as_user(factories.user())

	with db_diff() as d:
		client.post("/api_keys", {"name": factories.unique("app"), "redirect_uri": "https://example.com/callback", "description": factories.unique()})

	notice = d.inserted["comments"][0]["id"] if d.inserted.get("comments") else None
	d.assert_exactly(inserted={
		"oauth_apps": [{}],
		"comments": [{"id": notice, "author_id": seed.SYSTEM_ID, "sentto": seed.MODMAIL_ID, "parent_submission": None, "level": 1, "top_comment_id": notice}],
		"notifications": [{"user_id": admin["id"], "comment_id": notice} for admin in receivers],
	})


@pytest.mark.parametrize("via", ["contact form", "api keys"])
def test_an_admin_writing_modmail_isnt_notified_of_it(via):
	writer, other = factories.admin(3), factories.admin(2)
	client = as_user(writer)

	if via == "contact form": client.post("/send_admin", {"message": factories.unique()})
	else: client.post("/api_keys", {"name": factories.unique("app"), "redirect_uri": "https://example.com/callback", "description": factories.unique()})

	message = db.rows("comments", sentto=seed.MODMAIL_ID)[-1]
	assert [n["user_id"] for n in db.rows("notifications", comment_id=message["id"])] == [other["id"]]


# The modmail page

def test_logged_out_visitors_are_sent_to_log_in():
	assert_login_redirect(anon().get("/notifications/modmail"), "/notifications/modmail")


@pytest.mark.parametrize("level", [0, 1])
def test_below_level_2_is_refused(level):
	assert_status(as_user(factories.user(admin_level=level)).get("/notifications/modmail"), 403)


def test_api_clients_are_refused():
	assert_status(as_api(factories.api_token(factories.admin(3))).get("/notifications/modmail"), 403)


@pytest.mark.parametrize("level", [2, 3])
def test_lists_modmail_newest_first(level):
	older = factories.message(factories.user(), seed.MODMAIL_ID)
	newer = factories.message(factories.user(), seed.MODMAIL_ID)
	direct = factories.message(factories.user(), factories.user())

	r = as_user(factories.admin(level)).get("/notifications/modmail")

	assert_html(r, 200)
	assert_in_order(r, [newer["text"], older["text"]])
	assert_not_in_payload(r, direct["text"])


def test_shows_each_conversations_replies():
	starter = factories.user()
	message = factories.message(starter, seed.MODMAIL_ID)
	reply = factories.message(factories.admin(3), seed.MODMAIL_ID, message)

	assert_in_order(as_user(factories.admin(2)).get("/notifications/modmail"), [message["text"], reply["text"]])


def test_showing_modmail_marks_it_read():
	admin = factories.admin(2)
	message = factories.message(factories.user(), seed.MODMAIL_ID)
	answer = factories.message(factories.admin(3), seed.MODMAIL_ID, message)
	for m in (message, answer):
		factories.notification(admin, m)
	client = as_user(admin)

	with db_diff() as d:
		client.get("/notifications/modmail")

	d.assert_exactly(updated={"notifications": {(admin["id"], m["id"]): {"read": True} for m in (message, answer)}})


def test_pages_hold_25():
	messages = [factories.message(factories.user(), seed.MODMAIL_ID) for _ in range(26)]
	client = as_user(factories.admin(2))

	first, second = client.get("/notifications/modmail"), client.get("/notifications/modmail", params={"page": 2})

	assert_in_payload(first, messages[1]["text"])
	assert_not_in_payload(first, messages[0]["text"])
	assert_in_payload(second, messages[0]["text"])
	assert_not_in_payload(second, messages[1]["text"])

