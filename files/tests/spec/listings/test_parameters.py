'''
How the listings read their parameters: the front page (GET /), /changelog, /comments, the three searches and a profile's posts and comments (GET /@<username>/posts, GET /@<username>/).

- "page" counts from 1: zero, a negative number or anything that isn't a whole number means the first page. A page past the last is empty, however far past. The same goes for the profile, saved, voter, moderation queue, mod log, feed and API application listings.
- "sort" and "t" are read in any letter case. An unknown "sort" lists newest first, and an unknown "t" means all time; the page's links carry the sort and time window in use, never the unknown values.
- On the front page and /comments, an "after" or "before" that isn't a whole number is ignored.
'''
import re
import time

import pytest

from files.tests.spec.harness import *

NOW = int(time.time())


def _changelog(**overrides):
	sentinel = factories.unique()
	return {**factories.post(factories.admin(1), title=f"[changelog] zebra {sentinel}", **overrides), "sentinel": sentinel}


def _post(author=None, **overrides):
	sentinel = factories.unique()
	return {**factories.post(author or factories.user(), title=f"zebra {sentinel}", **overrides), "sentinel": sentinel}


def _comment(author=None, **overrides):
	sentinel = factories.unique()
	return {**factories.comment(author or factories.user(), factories.post(factories.user()), body=f"zebra {sentinel}", **overrides), "sentinel": sentinel}


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


@pytest.mark.parametrize("path", [*LISTINGS, "/search/users"])
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


def _profile_path(kind):
	author = factories.user()
	return author, f"/@{author['username']}/posts" if kind == "posts" else f"/@{author['username']}/"


def _links(r):
	return re.findall(r'href="([^"]*)"', r.text)


@pytest.mark.parametrize("path", [*LISTINGS, "/search/users", "profile posts", "profile comments"])
def test_unknown_sort_and_time_filter_are_not_put_into_links(path):
	sort, t = factories.unique("sort"), factories.unique("t")
	if path.startswith("profile"):
		_, path = _profile_path(path.split()[1])
		r = anon().get(path, params={"sort": sort, "t": t})
	else:
		r = as_user(factories.user()).get(path, params={**LISTINGS.get(path, (None, {"q": "zebra"}))[1], "sort": sort, "t": t})

	assert_status(r, 200)
	assert not [link for link in _links(r) if sort in link or t in link]


@pytest.mark.parametrize("path", [*LISTINGS, "profile posts", "profile comments"])
def test_sort_and_time_filter_ignore_letter_case(path):
	if path.startswith("profile"):
		kind = path.split()[1]
		author, path = _profile_path(kind)
		make = (lambda **o: _post(author=author, **o)) if kind == "posts" else (lambda **o: _comment(author=author, **o))
		client = anon()
		extra = {}
	else:
		make, extra = LISTINGS[path]
		client = as_user(factories.user())
	older = make(created_utc=int(time.time()) - 7200)
	newer = make(created_utc=int(time.time()) - 60)
	too_old = make(created_utc=int(time.time()) - 3 * 86400)

	r = client.get(path, params={**extra, "sort": "OLD", "t": "Day"})

	assert_in_order(r, [older["sentinel"], newer["sentinel"]])
	assert_not_in_payload(r, too_old["sentinel"])


@pytest.mark.parametrize("path", [*LISTINGS, "/search/users"])
@pytest.mark.parametrize("page", ["5", str(10**20)])
def test_a_page_past_the_last_is_empty(path, page):
	if path == "/search/users":
		user = factories.user(username=f"zebra{factories.unique('u')}")
		token = f"/@{user['username']}\""
		r = as_user(factories.user()).get(path, params={"q": "zebra", "page": page})
	else:
		token = LISTINGS[path][0](created_utc=NOW - 60)["sentinel"]
		r = _get(path, page=page)

	assert_status(r, 200)
	assert_not_in_payload(r, token)


def _other_listing(kind, viewer):
	'''Arranges an item that the listing `kind` shows `viewer` on its first page; returns (path, a sentinel of the item).'''
	name = viewer["username"]
	if kind == "profile posts":
		return f"/@{name}/posts", factories.post(viewer)["title"]
	if kind == "profile comments":
		return f"/@{name}/", factories.comment(viewer, factories.post(factories.user()))["body"]
	if kind == "saved posts":
		post = factories.post(factories.user())
		db.insert("save_relationship", user_id=viewer["id"], submission_id=post["id"])
		return f"/@{name}/saved/posts", post["title"]
	if kind == "saved comments":
		comment = factories.comment(factories.user(), factories.post(factories.user()))
		db.insert("comment_save_relationship", user_id=viewer["id"], comment_id=comment["id"])
		return f"/@{name}/saved/comments", comment["body"]
	if kind == "voter drilldown":
		voter = factories.user()
		post = factories.post(viewer)
		factories.vote(voter, post, 1)
		return f"/@{name}/upvoters/{voter['id']}/posts", post["title"]
	if kind == "admin queue":
		return "/admin/removed/posts", factories.post(factories.user(), state_mod="REMOVED", state_mod_set_by="somemod")["title"]
	if kind == "feed":
		return "/rss", factories.post(factories.user(), body="text")["title"]
	if kind == "mod log":
		return "/log", None
	application = factories.oauth_app(factories.user())
	if kind == "app posts":
		return f"/admin/app/{application['id']}", factories.post(factories.user(), app_id=application["id"])["title"]
	return f"/admin/app/{application['id']}/comments", factories.comment(factories.user(), factories.post(factories.user()), app_id=application["id"])["body"]


OTHER_LISTINGS = ["profile posts", "profile comments", "saved posts", "saved comments", "voter drilldown", "admin queue", "feed", "mod log", "app posts", "app comments"]


@pytest.mark.parametrize("kind", OTHER_LISTINGS)
@pytest.mark.parametrize("page", ["abc", str(10**20)])
def test_other_listings_read_pages_alike(kind, page):
	viewer = factories.admin(3)
	path, token = _other_listing(kind, viewer)

	r = as_user(viewer).get(path, params={"page": page})

	assert_status(r, 200)
	if token: (assert_in_payload if page == "abc" else assert_not_in_payload)(r, token)
