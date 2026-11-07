'''
How a conversation's messages show wherever its thread is shown (the Messages and modmail tabs, a message's page), in pages and JSON alike: by the rule comments follow on posts.
- A message its sender deleted shows as deleted, and the answers under it still show.
- A removed message shows as removed, except to admins from level 2, who see it whole.
- A shadowbanned sender's messages show to the sender and to admins from level 2; to others they show as removed, with the answers under them.
'''
import pytest

from files.tests.spec.harness import *

DELETED = {"state_user_deleted_utc": "2020-01-01T00:00:00Z"}


def _thread(starter, recipient, answerer, **middle):
	'''A first message from `starter` to `recipient` (a user, or modmail), `answerer`'s answer to it (with `middle` overrides) and the starter's answer to that.'''
	top = factories.message(starter, recipient, created_utc=1000)
	answer = factories.message(answerer, recipient if recipient == seed.MODMAIL_ID else starter, top, created_utc=1001, **middle)
	last = factories.message(starter, recipient, answer, created_utc=1002)
	return top, answer, last


def _direct(**middle):
	starter, other = factories.user(), factories.user()
	return (starter, other, *_thread(starter, other, other, **middle))


PAGES = {
	"messages tab": lambda top: "/notifications/messages",
	"message page": lambda top: f"/comment/{top['id']}",
}


@pytest.mark.parametrize("page", PAGES)
def test_answers_under_a_deleted_message_still_show(page):
	starter, other, top, answer, last = _direct(**DELETED)

	r = as_user(starter).get(PAGES[page](top))

	assert_html(r, 200)
	assert_not_in_payload(r, answer["text"])
	assert_in_order(r, [top["text"], last["text"]])


def test_answers_under_a_deleted_message_are_in_the_json():
	starter, other, top, answer, last = _direct(**DELETED)

	r = as_api(factories.api_token(starter)).get("/notifications/messages")

	assert_status(r, 200)
	[conversation] = r.json["data"]
	[shown_answer] = conversation["replies"]
	assert shown_answer["id"] == answer["id"] and "body_html" not in shown_answer
	assert [reply["id"] for reply in shown_answer["replies"]] == [last["id"]]


@pytest.mark.parametrize("page", PAGES)
def test_a_removed_message_shows_as_removed_to_the_other_user(page):
	starter, other, top, answer, last = _direct(state_mod="REMOVED", state_mod_set_by="somemod")

	r = as_user(starter).get(PAGES[page](top))

	assert_not_in_payload(r, answer["text"])
	assert_in_order(r, [top["text"], last["text"]])


def test_admins_see_removed_modmail_whole():
	starter = factories.user()
	top, answer, last = _thread(starter, seed.MODMAIL_ID, factories.admin(3), state_mod="REMOVED", state_mod_set_by="somemod")

	r = as_user(factories.admin(2)).get("/notifications/modmail")

	assert_in_order(r, [top["text"], answer["text"], last["text"]])


@pytest.mark.parametrize("page", PAGES)
def test_shadowbanned_senders_see_their_own_messages(page):
	starter, other = factories.user(), factories.user(shadowbanned="somemod")
	top, answer, last = _thread(starter, other, other)

	r = as_user(other).get(PAGES[page](top))

	assert_in_order(r, [top["text"], answer["text"], last["text"]])


@pytest.mark.parametrize("page", PAGES)
def test_shadowbanned_senders_messages_are_hidden_from_the_other_user(page):
	starter, other = factories.user(), factories.user(shadowbanned="somemod")
	top, answer, last = _thread(starter, other, other)

	r = as_user(starter).get(PAGES[page](top))

	assert_not_in_payload(r, answer["text"])
	assert_in_order(r, [top["text"], last["text"]])


def test_admins_see_shadowbanned_senders_modmail():
	starter, shadowbanned_admin = factories.user(), factories.admin(3, shadowbanned="somemod")
	top, answer, last = _thread(starter, seed.MODMAIL_ID, shadowbanned_admin)

	r = as_user(factories.admin(2)).get("/notifications/modmail")

	assert_in_order(r, [top["text"], answer["text"], last["text"]])
