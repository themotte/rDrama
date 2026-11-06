'''
GET /comments lists comments on posts across the site, for logged-in users only (others are sent to log in).

25 comments to a page, "page" (from 1) choosing the page. "sort" orders them as post listings do (test_front), with comments meaning most replies first and ties falling back to newest first; newest first by default. "t" keeps only comments created within that long, all time by default; "after" and "before" (Unix times) instead keep only comments created strictly after or before.

Which comments a viewer may see is in test_visibility. Replies aren't shown under the comments they reply to.

An API client gets {"data": [...]}: the page's comments as JSON objects.
'''
import time

import pytest

from files.tests.spec.harness import *

NOW = int(time.time())


def _comment(**overrides):
	return factories.comment(factories.user(), factories.post(factories.user()), **overrides)


def test_logged_out_visitors_are_sent_to_log_in():
	assert_login_redirect(anon().get("/comments"), "/comments")


def test_lists_comments_newest_first():
	older = _comment(created_utc=NOW - 7200)
	newer = _comment(created_utc=NOW - 60)

	r = as_user(factories.user()).get("/comments")

	assert_html(r, 200)
	assert_in_order(r, [newer["body"], older["body"]])


SORTS = {
	"new": ({"created_utc": NOW - 60}, {"created_utc": NOW - 7200}),
	"old": ({"created_utc": NOW - 7200}, {"created_utc": NOW - 60}),
	"top": ({"upvotes": 5, "created_utc": NOW - 7200}, {"upvotes": 2, "created_utc": NOW - 60}),
	"bottom": ({"upvotes": 1, "downvotes": 3, "created_utc": NOW - 7200}, {"upvotes": 2, "created_utc": NOW - 60}),
	"controversial": ({"upvotes": 5, "downvotes": 5, "created_utc": NOW - 7200}, {"upvotes": 10, "created_utc": NOW - 60}),
	"comments": ({"descendant_count": 5, "created_utc": NOW - 7200}, {"descendant_count": 2, "created_utc": NOW - 60}),
	"hot": ({"upvotes": 1000, "created_utc": NOW - 3600}, {"upvotes": 1, "created_utc": NOW}),
}


@pytest.mark.parametrize("sort", SORTS)
def test_sorts(sort):
	first_overrides, second_overrides = SORTS[sort]
	first = _comment(**first_overrides)
	second = _comment(**second_overrides)

	r = as_user(factories.user()).get("/comments", params={"sort": sort})

	assert_in_order(r, [first["body"], second["body"]])


@pytest.mark.parametrize("sort", ["top", "bottom", "controversial", "comments"])
def test_ties_list_newest_first(sort):
	older = _comment(created_utc=NOW - 7200)
	newer = _comment(created_utc=NOW - 60)

	r = as_user(factories.user()).get("/comments", params={"sort": sort})

	assert_in_order(r, [newer["body"], older["body"]])


def test_time_filter():
	now = int(time.time())
	inside = _comment(created_utc=now - 3000)
	outside = _comment(created_utc=now - 4000)

	r = as_user(factories.user()).get("/comments", params={"t": "hour"})

	assert_in_payload(r, inside["body"])
	assert_not_in_payload(r, outside["body"])


def test_all_time_by_default():
	ancient = _comment(created_utc=1)

	r = as_user(factories.user()).get("/comments")

	assert_in_payload(r, ancient["body"])


def test_after_and_before_replace_the_time_filter():
	early, middle, late = _comment(created_utc=NOW - 9000), _comment(created_utc=NOW - 8000), _comment(created_utc=NOW - 7000)

	r = as_user(factories.user()).get("/comments", params={"t": "hour", "after": NOW - 9000, "before": NOW - 7000})

	assert_in_payload(r, middle["body"])
	assert_not_in_payload(r, early["body"])
	assert_not_in_payload(r, late["body"])


def test_pages_hold_25():
	comments = [_comment(created_utc=NOW - 60 * (i + 1)) for i in range(26)]
	client = as_user(factories.user())

	first, second = client.get("/comments"), client.get("/comments", params={"page": 2})

	assert_in_payload(first, comments[24]["body"])
	assert_not_in_payload(first, comments[25]["body"])
	assert_in_payload(second, comments[25]["body"])
	assert_not_in_payload(second, comments[24]["body"])


def test_replies_are_not_shown_under_their_parents():
	post = factories.post(factories.user())
	parent = factories.comment(factories.user(), post, created_utc=NOW - 7200)
	reply = factories.comment(factories.user(), post, parent, created_utc=NOW - 60)
	for i in range(25):
		_comment(created_utc=NOW - 120 - i)

	r = as_user(factories.user()).get("/comments", params={"page": 2})

	assert_in_payload(r, parent["body"])
	assert_not_in_payload(r, reply["body"])


def test_api_clients_get_json():
	newer = _comment(created_utc=NOW - 60)
	older = _comment(created_utc=NOW - 7200)

	r = as_api(factories.api_token(factories.user())).get("/comments")

	assert_status(r, 200)
	assert set(r.json) == {"data"}
	assert [c["id"] for c in r.json["data"]] == [newer["id"], older["id"]]
