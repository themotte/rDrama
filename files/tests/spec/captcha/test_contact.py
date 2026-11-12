'''
With a site key, the contact form (GET /contact, /press, /media) asks visitors for an hCaptcha answer, and POST /send_admin hears a visitor (notifications/test_modmail.py) only once hCaptcha approves the answer; otherwise it refuses with 403. Members, and API clients, aren't asked, and members' pages don't load hCaptcha's script. The answer is checked after the form's own checks, which refuse without asking hCaptcha: an empty message or a file that isn't a readable image (400, notifications/test_modmail.py), a link to a banned domain (403) or too many mentions (400, rendering/). A visitor refused, for whatever reason, leaves no upload behind.
'''
import os

import pytest

from files.tests.spec.harness import *
from files.tests.spec.harness import captcha

pytestmark = pytest.mark.profile("captcha")


def _send(client, files=None, **fields):
	return client.post_raw("/send_admin", {"message": factories.unique("message"), **fields}, files=files)


@pytest.mark.parametrize("path", ["/contact", "/press", "/media"])
def test_the_form_offers_visitors_the_captcha(path):
	r = anon().get(path)

	assert_html(r, 200)
	assert_in_payload(r, captcha.SITE_KEY)
	assert_in_payload(r, captcha.WIDGET_SCRIPT)


@pytest.mark.parametrize("path", ["/contact", "/press", "/media"])
def test_the_form_doesnt_offer_members_the_captcha(path):
	r = as_user(factories.user()).get(path)

	assert_html(r, 200)
	assert_not_in_payload(r, captcha.SITE_KEY)
	assert_not_in_payload(r, captcha.WIDGET_SCRIPT)


def test_a_visitor_hcaptcha_approves_is_heard():
	captcha.answer(True)
	text, answer = factories.unique("message"), factories.unique("answer")

	r = anon().post_raw("/send_admin", {"message": text, captcha.FIELD: answer})

	assert_html(r, 200)
	assert text in db.row("comments", author_id=seed.SYSTEM_ID, sentto=seed.MODMAIL_ID)["body_html"]
	captcha.assert_checked(answer)


def test_the_reply_to_a_visitor_offers_the_captcha_again():
	captcha.answer(True)

	r = _send(anon(), **{captcha.FIELD: factories.unique("answer")})

	assert_html(r, 200)
	assert_in_payload(r, captcha.SITE_KEY)
	assert_in_payload(r, captcha.WIDGET_SCRIPT)


def test_a_visitor_hcaptcha_refuses_is_refused():
	captcha.answer(False)
	answer = factories.unique("answer")

	with db_diff() as d:
		r = _send(anon(), **{captcha.FIELD: answer})

	assert_status(r, 403)
	d.assert_exactly()
	captcha.assert_checked(answer)


@pytest.mark.parametrize("fields", [{}, {captcha.FIELD: ""}], ids=["absent", "empty"])
def test_a_visitor_without_an_answer_is_refused_without_asking(fields):
	captcha.answer(True)

	with db_diff() as d:
		r = _send(anon(), **fields)

	assert_status(r, 403)
	d.assert_exactly()
	assert external_web.requests() == []


@pytest.mark.parametrize("failure", captcha.FAILURES)
def test_a_visitor_whose_answer_cant_be_checked_is_refused(failure):
	captcha.fail(failure)

	with db_diff() as d:
		r = _send(anon(), **{captcha.FIELD: factories.unique("answer")})

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("kind", ["member", "API client"])
def test_members_are_heard_without_being_asked(kind):
	captcha.answer(False)
	user = factories.user()
	client = as_user(user) if kind == "member" else as_api(factories.api_token(user))
	text = factories.unique("message")

	r = client.post("/send_admin", {"message": text})

	assert_status(r, 200)
	assert text in db.row("comments", author_id=user["id"], sentto=seed.MODMAIL_ID)["body_html"]
	assert external_web.requests() == []


def test_a_member_posting_without_their_form_key_is_heard_as_a_visitor():
	captcha.answer(True)
	user = factories.user()
	text, answer = factories.unique("message"), factories.unique("answer")

	r = as_user(user).post_raw("/send_admin", {"message": text, captcha.FIELD: answer})

	assert_html(r, 200)
	assert text in db.row("comments", author_id=seed.SYSTEM_ID, sentto=seed.MODMAIL_ID)["body_html"]
	captcha.assert_checked(answer)


def _banned_link():
	domain = f"{factories.unique('banned')}.com"
	db.insert("banneddomains", domain=domain, reason="spam")
	return {"message": f"see https://{domain}/x"}


@pytest.mark.parametrize("form, status", [
	(lambda: ({"message": ""}, None), 400),
	(lambda: ({}, {"file": uploads.text_file()}), 400),
	(lambda: ({}, {"file": uploads.truncated_png()}), 400),
	(lambda: (_banned_link(), None), 403),
], ids=["empty message", "not an image", "unreadable image", "banned domain"])
def test_the_forms_own_checks_come_before_the_captcha(form, status):
	fields, files = form()

	with db_diff() as d:
		r = _send(anon(), files=files, **{captcha.FIELD: factories.unique("answer"), **fields})

	assert_status(r, status)
	d.assert_exactly()
	assert external_web.requests() == []
	assert os.listdir(config.images_dir()) == []


def test_a_visitor_hcaptcha_refuses_leaves_no_upload():
	captcha.answer(False)

	with db_diff() as d:
		r = _send(anon(), files={"file": uploads.png(2, 2)}, **{captcha.FIELD: factories.unique("answer")})

	assert_status(r, 403)
	d.assert_exactly()
	assert os.listdir(config.images_dir()) == []
