'''
Who sees reports. While an item's reports are open (REPORTED), admins of level 2 and up see each of its reports, its reporter's name and its reason, wherever the item shows: a post on its page and in post listings, a comment wherever it renders. Nobody else sees them, and nobody sees them once the reports are resolved or ignored.

Beside an open comment's reports, those admins also see the volunteers' verdict on it, from its volunteer badness b (see the volunteer area): unknown for 0.4 < b < 0.6, bad from 0.6, not bad up to 0.4, with a confidence of round(-10 * log2(1 - 2 * |b - 0.5|)).
'''
import re

import pytest

from files.tests.spec.harness import *

VIEWERS = {
	"user": lambda: factories.user(),
	"helper": lambda: factories.admin(1),
	"admin": lambda: factories.admin(2),
}


def _reported_post(state="REPORTED"):
	post = factories.post(factories.user(), state_report=state)
	reporter = factories.user()
	reason = factories.report(reporter, post)["reason"]
	return post, reporter, reason


def _reported_comment(state="REPORTED", **overrides):
	post = factories.post(factories.user())
	comment = factories.comment(factories.user(), post, state_report=state, **overrides)
	reporter = factories.user()
	reason = factories.report(reporter, comment)["reason"]
	return post, reporter, reason


PAGES = {
	"post page": lambda post: f"/post/{post['id']}",
	"front page": lambda post: "/",
}


@pytest.mark.parametrize("page", PAGES)
def test_admins_see_a_posts_open_reports(page):
	post, reporter, reason = _reported_post()

	r = as_user(factories.admin(2)).get(PAGES[page](post))

	assert_html(r, 200)
	assert_in_payload(r, reason)
	assert_in_payload(r, reporter["username"])


def test_admins_see_a_comments_open_reports():
	post, reporter, reason = _reported_comment()

	r = as_user(factories.admin(2)).get(f"/post/{post['id']}")

	assert_html(r, 200)
	assert_in_payload(r, reason)
	assert_in_payload(r, reporter["username"])


@pytest.mark.parametrize("viewer", ["user", "helper"])
@pytest.mark.parametrize("page", PAGES)
def test_others_never_see_a_posts_reports(page, viewer):
	post, reporter, reason = _reported_post()

	r = as_user(VIEWERS[viewer]()).get(PAGES[page](post))

	assert_html(r, 200)
	assert_not_in_payload(r, reason)
	assert_not_in_payload(r, reporter["username"])


@pytest.mark.parametrize("viewer", ["user", "helper"])
def test_others_never_see_a_comments_reports(viewer):
	post, reporter, reason = _reported_comment()

	r = as_user(VIEWERS[viewer]()).get(f"/post/{post['id']}")

	assert_html(r, 200)
	assert_not_in_payload(r, reason)
	assert_not_in_payload(r, reporter["username"])


@pytest.mark.parametrize("state", ["UNREPORTED", "RESOLVED", "IGNORED"])
@pytest.mark.parametrize("page", PAGES)
def test_reports_of_a_post_whose_reports_are_closed_dont_show(page, state):
	post, reporter, reason = _reported_post(state)

	r = as_user(factories.admin(2)).get(PAGES[page](post))

	assert_html(r, 200)
	assert_not_in_payload(r, reason)


@pytest.mark.parametrize("state", ["UNREPORTED", "RESOLVED", "IGNORED"])
def test_reports_of_a_comment_whose_reports_are_closed_dont_show(state):
	post, reporter, reason = _reported_comment(state)

	r = as_user(factories.admin(2)).get(f"/post/{post['id']}")

	assert_html(r, 200)
	assert_not_in_payload(r, reason)


def test_admins_see_shadowbanned_users_reports():
	post = factories.post(factories.user(), state_report="REPORTED")
	reporter = factories.user(shadowbanned="somemod")
	reason = factories.report(reporter, post)["reason"]

	r = as_user(factories.admin(2)).get(f"/post/{post['id']}")

	assert_html(r, 200)
	assert_in_payload(r, reason)


def _comment_by_badness(viewer, badnesses):
	'''The text of one reported comment on its post's page, seen by `viewer` with the comment's volunteer badness at each of `badnesses` in turn.'''
	post = factories.post(factories.user())
	comment = factories.comment(factories.user(), post, state_report="REPORTED", created_utc=1000)
	factories.report(factories.user(), comment)
	client = as_user(viewer)
	texts = []
	for badness in badnesses:
		db.update("comments", {"id": comment["id"]}, volunteer_janitor_badness=badness)
		r = client.get(f"/post/{post['id']}")
		assert_html(r, 200)
		texts.append(element_text(r, f"comment-{comment['id']}"))
	return texts


@pytest.mark.parametrize("same", [(0.45, 0.55), (0.41, 0.59), (0.95, 0.9505), (0.05, 0.0495)], ids=["unknown either side", "unknown band", "same confidence bad", "same confidence not bad"])
def test_the_verdict_shows_the_band_and_confidence(same):
	a, b = _comment_by_badness(factories.admin(2), same)

	assert a == b


@pytest.mark.parametrize("different", [(0.5, 0.6), (0.5, 0.4), (0.4, 0.6), (0.95, 0.97), (0.05, 0.03)], ids=["unknown-bad", "unknown-not bad", "not bad-bad", "bad confidence", "not bad confidence"])
def test_admins_see_the_volunteers_verdict(different):
	a, b = _comment_by_badness(factories.admin(2), different)

	assert a != b


@pytest.mark.parametrize("badness, confidence", [(0.95, "33"), (0.05, "33"), (0.97, "41")])
def test_the_confidence_shows_as_its_number(badness, confidence):
	text, = _comment_by_badness(factories.admin(2), [badness])

	assert re.search(rf"\b{confidence}\b", text), text


def test_others_see_no_verdict():
	a, b = _comment_by_badness(factories.user(), (0.05, 0.95))

	assert a == b
