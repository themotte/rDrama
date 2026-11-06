'''
How the listings read their parameters: the front page (GET /), /changelog, /comments and the three searches.

- "page" counts from 1: zero or a negative number means the first page. Anything else that isn't a whole number also means the first page, except on the front page.
- An unknown "sort" lists newest first, and an unknown "t" means all time.
- On the front page and /comments, an "after" or "before" that isn't a whole number is ignored.
'''
import time

import pytest

from files.tests.spec.harness import *

NOW = int(time.time())


def _changelog(**overrides):
	sentinel = factories.unique()
	return {**factories.post(factories.admin(1), title=f"[changelog] zebra {sentinel}", **overrides), "sentinel": sentinel}


def _post(**overrides):
	sentinel = factories.unique()
	return {**factories.post(factories.user(), title=f"zebra {sentinel}", **overrides), "sentinel": sentinel}


def _comment(**overrides):
	sentinel = factories.unique()
	return {**factories.comment(factories.user(), factories.post(factories.user()), body=f"zebra {sentinel}", **overrides), "sentinel": sentinel}


LISTINGS = {
	"/": (_post, {}),
	"/changelog": (_changelog, {}),
	"/comments": (_comment, {}),
	"/search/posts": (_post, {"q": "zebra"}),
	"/search/comments": (_comment, {"q": "zebra"}),
}


def _get(path, **params):
	return as_user(factories.user()).get(path, params={**LISTINGS[path][1], **params})


@pytest.mark.parametrize("path", LISTINGS)
@pytest.mark.parametrize("page", ["0", "-3"])
def test_pages_below_one_mean_the_first(path, page):
	make = LISTINGS[path][0]
	newest = make(created_utc=NOW - 60)

	r = _get(path, page=page)

	assert_status(r, 200)
	assert_in_payload(r, newest["sentinel"])


@pytest.mark.parametrize("path", [p for p in LISTINGS if p != "/"] + ["/search/users"])
@pytest.mark.parametrize("page", ["abc", "1.5", ""])
def test_pages_that_are_not_numbers_mean_the_first(path, page):
	if path == "/search/users":
		user = factories.user(username=f"zebra{factories.unique('u')}")
		token = f"/@{user['username']}\""
		r = as_user(factories.user()).get(path, params={"q": "zebra", "page": page})
	else:
		token = LISTINGS[path][0](created_utc=NOW - 60)["sentinel"]
		r = _get(path, page=page)

	assert_status(r, 200)
	assert_in_payload(r, token)


@pytest.mark.parametrize("path", LISTINGS)
def test_an_unknown_sort_lists_newest_first(path):
	make = LISTINGS[path][0]
	older = make(created_utc=NOW - 7200, upvotes=50)
	newer = make(created_utc=NOW - 60)

	r = _get(path, sort="sideways")

	assert_status(r, 200)
	assert_in_order(r, [newer["sentinel"], older["sentinel"]])


@pytest.mark.parametrize("path", LISTINGS)
def test_an_unknown_time_filter_means_all_time(path):
	make = LISTINGS[path][0]
	ancient = make(created_utc=1)

	r = _get(path, t="fortnight")

	assert_status(r, 200)
	assert_in_payload(r, ancient["sentinel"])


@pytest.mark.parametrize("path", ["/", "/comments"])
@pytest.mark.parametrize("bound", ["after", "before"])
def test_bounds_that_are_not_numbers_are_ignored(path, bound):
	make = LISTINGS[path][0]
	item = make(created_utc=int(time.time()) - 60)

	r = _get(path, t="hour", **{bound: "yesterday"})

	assert_status(r, 200)
	assert_in_payload(r, item["sentinel"])
