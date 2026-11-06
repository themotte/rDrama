'''
The front page, GET / (also GET /catalog), lists posts for anyone, logged in or not.

- A page holds the viewer's front page size ("frontsize": 15, 25, 50 or 100; 25 when logged out), and "page" (from 1) chooses the page.
- "sort" orders the posts: new (newest first), old, top (highest score first), bottom, controversial (closest to evenly split votes first), comments (most comments first), hot (score weighed against age). Without "sort", a logged-in viewer gets their default sort ("defaultsorting") and anyone else new. Ties fall back to newest first.
- "t" (hour, day, week, month, year, all) keeps only posts created within that long (a month is 30 days, a year 365). "after" and "before" (Unix times) instead keep only posts created strictly after or before that time; with either, "t" doesn't apply.
- Pinned posts come first, above the sorted list, on the first page when neither "after" nor "before" is given; they are then left out of the sorted list on every page, so the first page still holds a full page besides them. Pins ignore the sort, the time window, filter words and the changelog subscription. With "after" or "before", pinned posts are sorted with the rest. A pin made with an expiry time stops being pinned once that time has passed.
- Changelog posts (see test_changelog) are left out unless the viewer subscribes to the changelog.
- Posts whose title contains one of the viewer's filter words (one per line of "custom_filter_list", in any letter case) are left out.
- A viewer who hides what they voted on ("hidevotedon") doesn't get posts they voted up or down, pinned ones included.

Which posts a viewer may see is in test_visibility.

An API client gets {"data": [...], "next_exists": ...}: the page's posts as JSON objects, and whether a further page exists.
'''
import time

import pytest

from files.tests.spec.harness import *

NOW = int(time.time())


def _post(**overrides):
	return factories.post(factories.user(), **overrides)


def test_logged_out_visitors_get_the_front_page():
	post = _post()

	r = anon().get("/")

	assert_html(r, 200)
	assert_in_payload(r, post["title"])


def test_catalog_is_the_front_page():
	post = _post()

	r = as_user(factories.user()).get("/catalog")

	assert_html(r, 200)
	assert_in_payload(r, post["title"])


# Sorting

SORTS = {
	"new": ({"created_utc": NOW - 60}, {"created_utc": NOW - 7200}),
	"old": ({"created_utc": NOW - 7200}, {"created_utc": NOW - 60}),
	"top": ({"upvotes": 5, "created_utc": NOW - 7200}, {"upvotes": 2, "created_utc": NOW - 60}),
	"bottom": ({"upvotes": 1, "downvotes": 3, "created_utc": NOW - 7200}, {"upvotes": 2, "created_utc": NOW - 60}),
	"controversial": ({"upvotes": 5, "downvotes": 5, "created_utc": NOW - 7200}, {"upvotes": 10, "created_utc": NOW - 60}),
	"comments": ({"comment_count": 5, "created_utc": NOW - 7200}, {"comment_count": 2, "created_utc": NOW - 60}),
	"hot": ({"upvotes": 1000, "created_utc": NOW - 3600}, {"upvotes": 1, "created_utc": NOW}),
}


@pytest.mark.parametrize("sort", SORTS)
def test_sorts(sort):
	first_overrides, second_overrides = SORTS[sort]
	first = _post(**first_overrides)
	second = _post(**second_overrides)

	r = anon().get("/", params={"sort": sort})

	assert_html(r, 200)
	assert_in_order(r, [first["title"], second["title"]])


@pytest.mark.parametrize("sort", ["top", "bottom", "controversial", "comments"])
def test_ties_list_newest_first(sort):
	older = _post(created_utc=NOW - 7200)
	newer = _post(created_utc=NOW - 60)

	r = anon().get("/", params={"sort": sort})

	assert_in_order(r, [newer["title"], older["title"]])


def test_hot_weighs_score_against_age():
	old_popular = _post(upvotes=1000, created_utc=NOW - 30 * 86400)
	new_unvoted = _post(upvotes=1, created_utc=NOW - 60)

	r = anon().get("/", params={"sort": "hot"})

	assert_in_order(r, [new_unvoted["title"], old_popular["title"]])


def test_logged_out_visitors_get_newest_first():
	older = _post(created_utc=NOW - 7200)
	newer = _post(created_utc=NOW - 60)

	r = anon().get("/")

	assert_in_order(r, [newer["title"], older["title"]])


def test_logged_in_viewers_get_their_default_sort():
	older = _post(created_utc=NOW - 7200)
	newer = _post(created_utc=NOW - 60)

	r = as_user(factories.user(defaultsorting="old")).get("/")

	assert_in_order(r, [older["title"], newer["title"]])


def test_a_given_sort_overrides_the_default():
	older = _post(created_utc=NOW - 7200)
	newer = _post(created_utc=NOW - 60)

	r = as_user(factories.user(defaultsorting="old")).get("/", params={"sort": "new"})

	assert_in_order(r, [newer["title"], older["title"]])


# Time windows

WINDOWS = {"hour": 3600, "day": 86400, "week": 7 * 86400, "month": 30 * 86400, "year": 365 * 86400}


@pytest.mark.parametrize("t", WINDOWS)
def test_time_filter_keeps_posts_created_within_the_window(t):
	now = int(time.time())
	inside = _post(created_utc=now - WINDOWS[t] + 120)
	outside = _post(created_utc=now - WINDOWS[t] - 120)

	r = anon().get("/", params={"t": t})

	assert_in_payload(r, inside["title"])
	assert_not_in_payload(r, outside["title"])


def test_all_time_keeps_everything():
	ancient = _post(created_utc=1)

	r = anon().get("/", params={"t": "all"})

	assert_in_payload(r, ancient["title"])


def test_after_keeps_posts_created_strictly_after():
	at = _post(created_utc=NOW - 7200)
	later = _post(created_utc=NOW - 7199)

	r = anon().get("/", params={"after": NOW - 7200})

	assert_in_payload(r, later["title"])
	assert_not_in_payload(r, at["title"])


def test_before_keeps_posts_created_strictly_before():
	earlier = _post(created_utc=NOW - 7201)
	at = _post(created_utc=NOW - 7200)

	r = anon().get("/", params={"before": NOW - 7200})

	assert_in_payload(r, earlier["title"])
	assert_not_in_payload(r, at["title"])


@pytest.mark.parametrize("bound", ["after", "before"])
def test_after_and_before_replace_the_time_filter(bound):
	old = _post(created_utc=NOW - 7200)

	r = anon().get("/", params={"t": "hour", bound: NOW - 7201 if bound == "after" else NOW})

	assert_in_payload(r, old["title"])


# Pages

def _posts_newest_first(n):
	return [_post(created_utc=NOW - 60 * (i + 1)) for i in range(n)]


@pytest.mark.parametrize("frontsize", [15, 25, 50, 100])
def test_a_page_holds_the_viewers_front_page_size(frontsize):
	posts = _posts_newest_first(frontsize + 1)
	client = as_user(factories.user(frontsize=frontsize))

	first, second = client.get("/"), client.get("/", params={"page": 2})

	assert_in_payload(first, posts[frontsize - 1]["title"])
	assert_not_in_payload(first, posts[frontsize]["title"])
	assert_in_payload(second, posts[frontsize]["title"])
	assert_not_in_payload(second, posts[frontsize - 1]["title"])


def test_logged_out_pages_hold_25():
	posts = _posts_newest_first(26)

	r = anon().get("/")

	assert_in_payload(r, posts[24]["title"])
	assert_not_in_payload(r, posts[25]["title"])


# Pins

def test_pinned_posts_come_first():
	pinned = _post(stickied="someadmin", created_utc=NOW - 7200)
	newer = _post(created_utc=NOW - 60)

	r = anon().get("/", params={"sort": "new"})

	assert_in_order(r, [pinned["title"], newer["title"]])


def test_pins_come_first_whatever_the_sort():
	pinned = _post(stickied="someadmin", upvotes=0)
	top = _post(upvotes=50)

	r = anon().get("/", params={"sort": "top"})

	assert_in_order(r, [pinned["title"], top["title"]])


def test_pins_ignore_the_time_filter():
	pinned = _post(stickied="someadmin", created_utc=NOW - 30 * 86400)

	r = anon().get("/", params={"t": "day"})

	assert_in_payload(r, pinned["title"])


def test_pins_ignore_filter_words():
	pinned = _post(stickied="someadmin", title=f"spoilers {factories.unique()}")

	r = as_user(factories.user(custom_filter_list="spoilers")).get("/")

	assert_in_payload(r, pinned["title"])


def test_pinned_changelog_posts_show_without_a_subscription():
	pinned = factories.post(factories.admin(1), title=f"[changelog] {factories.unique()}", stickied="someadmin")

	r = as_user(factories.user(changelogsub=False)).get("/")

	assert_in_payload(r, pinned["title"])


def test_a_pin_within_its_time_is_pinned():
	pinned = _post(stickied="someadmin", stickied_utc=NOW + 3600, created_utc=NOW - 7200)
	newer = _post(created_utc=NOW - 60)

	r = anon().get("/")

	assert_in_order(r, [pinned["title"], newer["title"]])


def test_an_expired_pin_is_sorted_with_the_rest():
	expired = _post(stickied="someadmin", stickied_utc=NOW - 60, created_utc=NOW - 7200)
	newer = _post(created_utc=NOW - 60)

	r = anon().get("/")

	assert_in_order(r, [newer["title"], expired["title"]])


def test_the_first_page_holds_a_full_page_besides_the_pins():
	pinned = _post(stickied="someadmin", created_utc=NOW)
	posts = _posts_newest_first(16)

	r = as_user(factories.user(frontsize=15)).get("/")

	assert_in_order(r, [pinned["title"], posts[0]["title"]])
	assert_in_payload(r, posts[14]["title"])
	assert_not_in_payload(r, posts[15]["title"])


def test_pins_are_not_listed_again_on_later_pages():
	posts = _posts_newest_first(16)
	pinned = _post(stickied="someadmin", created_utc=NOW - 86400)

	r = as_user(factories.user(frontsize=15)).get("/", params={"page": 2})

	assert_in_payload(r, posts[15]["title"])
	assert_not_in_payload(r, pinned["title"])


@pytest.mark.parametrize("bound", ["after", "before"])
def test_with_after_or_before_pins_are_sorted_with_the_rest(bound):
	older = _post(created_utc=NOW - 7200)
	pinned = _post(stickied="someadmin", created_utc=NOW - 3600)
	newer = _post(created_utc=NOW - 60)

	r = anon().get("/", params={bound: NOW - 86400 if bound == "after" else NOW})

	assert_in_order(r, [newer["title"], pinned["title"], older["title"]])


# Changelog, filter words, hiding voted posts

def _changelog_post():
	return factories.post(factories.admin(1), title=f"[changelog] {factories.unique()}")


@pytest.mark.parametrize("viewer", ["visitor", "user"])
def test_changelog_posts_are_left_out_without_a_subscription(viewer):
	post = _changelog_post()

	r = (anon() if viewer == "visitor" else as_user(factories.user())).get("/")

	assert_html(r, 200)
	assert_not_in_payload(r, post["title"])


def test_changelog_subscribers_get_changelog_posts():
	post = _changelog_post()

	r = as_user(factories.user(changelogsub=True)).get("/")

	assert_in_payload(r, post["title"])


def test_filter_words_leave_out_posts_whose_titles_contain_them():
	token = factories.unique()
	filtered = _post(title=f"{token} about Spoilers today")
	kept = _post()

	r = as_user(factories.user(custom_filter_list="nothing\nspoilers")).get("/")

	assert_not_in_payload(r, token)
	assert_in_payload(r, kept["title"])


@pytest.mark.parametrize("vote", [1, -1])
def test_hiding_voted_posts_leaves_out_posts_voted_on(vote):
	viewer = factories.user(hidevotedon=True)
	voted = _post()
	factories.vote(viewer, voted, vote)
	other = _post()

	r = as_user(viewer).get("/")

	assert_not_in_payload(r, voted["title"])
	assert_in_payload(r, other["title"])


def test_hiding_voted_posts_leaves_out_pins_voted_on():
	viewer = factories.user(hidevotedon=True)
	pinned = _post(stickied="someadmin")
	factories.vote(viewer, pinned, 1)

	r = as_user(viewer).get("/")

	assert_not_in_payload(r, pinned["title"])


def test_voted_posts_are_listed_without_hiding():
	viewer = factories.user(hidevotedon=False)
	voted = _post()
	factories.vote(viewer, voted, 1)

	r = as_user(viewer).get("/")

	assert_in_payload(r, voted["title"])


# JSON

def test_api_clients_get_the_posts_as_json():
	newer = _post(created_utc=NOW - 60)
	older = _post(created_utc=NOW - 7200)
	client = as_api(factories.api_token(factories.user()))

	r = client.get("/")

	assert_status(r, 200)
	assert set(r.json) == {"data", "next_exists"}
	assert [p["id"] for p in r.json["data"]] == [newer["id"], older["id"]]
	assert r.json["next_exists"] is False


def test_a_listed_posts_json_is_its_post_json():
	post = _post(created_utc=NOW - 2 * 86400)
	client = as_api(factories.api_token(factories.user()))

	listed = client.get("/").json["data"][0]
	single = client.get(f"/post/{post['id']}").json

	assert listed == {k: v for k, v in single.items() if k != "replies"}


@pytest.mark.parametrize("count, further", [(25, False), (26, True)])
def test_json_tells_whether_a_further_page_exists(count, further):
	_posts_newest_first(count)

	r = as_api(factories.api_token(factories.user())).get("/")

	assert len(r.json["data"]) == 25
	assert r.json["next_exists"] is further
