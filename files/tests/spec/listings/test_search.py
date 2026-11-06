'''
Search, for logged-in users only (others are sent to log in): GET /search/posts, /search/comments and /search/users, each taking the query "q".

Requests whose User-Agent names a crawler (anything containing "bot", in any letter case, and also Bytespider and ChatGPT-User) are refused with 403.

Post and comment search:
- The words of the query must all appear, in any letter case and anywhere, in a post's title or a comment's text.
- Query terms of the form "key:value" narrow the search instead (others are searched as words): "author:<username>" keeps only that user's items, leaving out anonymous ones (an unknown user is a 404; a user with a private profile can be searched this way only by themselves and admins from level 2: API clients get a 403 and others a page with no results); "over18:" (with any value) keeps only items marked 18+; for posts, "domain:<domain>" keeps only link posts to https://<domain>, https://www.<domain> or https://old.<domain>, with or without a path.
- "sort" and "t" apply as on the front page (test_front), newest first and all time by default, 25 results to a page, "page" choosing the page.
- An API client gets {"total": ..., "data": [...]}: the number of matching items and the page's items as JSON objects.
- Which items a viewer may find is in test_visibility.

User search lists the users whose username contains the query (in any letter case, a leading "@" ignored): an exact match first, then those with the most followers, 25 to a page. An API client gets {"data": [...]}, the users as JSON objects.
'''
import time

import pytest

from files.tests.spec.harness import *

NOW = int(time.time())
PATHS = ["/search/posts", "/search/comments", "/search/users"]


@pytest.mark.parametrize("path", PATHS)
def test_logged_out_visitors_are_sent_to_log_in(path):
	assert_login_redirect(anon().get(path, params={"q": "x"}), f"{path}?q=x")


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("agent", ["Googlebot/2.1", "MyCustomBot/1.0", "SomeRobot", "Mozilla/5.0 (compatible; Bytespider)", "ChatGPT-User/1.0"])
def test_crawlers_are_refused(path, agent):
	r = as_user(factories.user()).get(path, params={"q": "x"}, headers={"User-Agent": agent})

	assert_status(r, 403)


@pytest.mark.parametrize("path", PATHS)
def test_browsers_may_search(path):
	assert_html(as_user(factories.user()).get(path, params={"q": "x"}), 200)


# Post and comment search

def _post(title_words="", author=None, **overrides):
	sentinel = factories.unique()
	post = factories.post(author or factories.user(), title=f"{title_words} {sentinel}".strip(), **overrides)
	return {**post, "sentinel": sentinel}


def _comment(body_words="", author=None, **overrides):
	sentinel = factories.unique()
	comment = factories.comment(author or factories.user(), factories.post(factories.user()), body=f"{body_words} {sentinel}".strip(), **overrides)
	return {**comment, "sentinel": sentinel}


KINDS = {"posts": _post, "comments": _comment}


def _search(kind, q, client=None, **params):
	return (client or as_user(factories.user())).get(f"/search/{kind}", params={"q": q, **params})


@pytest.mark.parametrize("kind", KINDS)
def test_every_word_must_appear_in_any_case(kind):
	both = KINDS[kind]("the Zebra crossed a road")
	one = KINDS[kind]("a zebra alone")

	r = _search(kind, "ROAD zebra")

	assert_in_payload(r, both["sentinel"])
	assert_not_in_payload(r, one["sentinel"])


@pytest.mark.parametrize("kind", KINDS)
def test_words_match_inside_longer_words(kind):
	item = KINDS[kind]("zebras")

	r = _search(kind, "ebra")

	assert_in_payload(r, item["sentinel"])


def test_post_search_does_not_search_bodies():
	post = _post(body="zebra in the body")

	r = _search("posts", "zebra")

	assert_not_in_payload(r, post["sentinel"])


@pytest.mark.parametrize("kind", KINDS)
def test_author_keeps_only_that_users_items(kind):
	author = factories.user()
	theirs = KINDS[kind]("zebra", author=author)
	others = KINDS[kind]("zebra")

	r = _search(kind, f"zebra author:{author['username']}")

	assert_in_payload(r, theirs["sentinel"])
	assert_not_in_payload(r, others["sentinel"])


@pytest.mark.parametrize("kind", KINDS)
def test_author_alone_lists_all_their_items(kind):
	author = factories.user()
	theirs = KINDS[kind](author=author)

	r = _search(kind, f"author:{author['username']}")

	assert_in_payload(r, theirs["sentinel"])


@pytest.mark.parametrize("kind", KINDS)
def test_author_leaves_out_their_anonymous_items(kind):
	author = factories.user()
	anonymous = KINDS[kind](author=author, ghost=True)

	r = _search(kind, f"author:{author['username']}")

	assert_not_in_payload(r, anonymous["sentinel"])


@pytest.mark.parametrize("kind", KINDS)
def test_anonymous_items_are_found_by_their_words(kind):
	anonymous = KINDS[kind]("zebra", ghost=True)

	r = _search(kind, "zebra")

	assert_in_payload(r, anonymous["sentinel"])


@pytest.mark.parametrize("kind", KINDS)
def test_other_key_value_terms_are_searched_as_words(kind):
	item = KINDS[kind]("zebra note:this")
	other = KINDS[kind]("zebra")

	r = _search(kind, "note:this")

	assert_in_payload(r, item["sentinel"])
	assert_not_in_payload(r, other["sentinel"])


@pytest.mark.parametrize("kind", KINDS)
def test_unknown_author_is_404(kind):
	assert_status(_search(kind, "author:nobodyatall"), 404)


@pytest.mark.parametrize("kind", KINDS)
def test_a_private_authors_items_are_not_found_by_author(kind):
	author = factories.user(is_private=True)
	item = KINDS[kind](author=author)

	r = _search(kind, f"author:{author['username']}")

	assert_html(r, 200)
	assert_not_in_payload(r, item["sentinel"])


@pytest.mark.parametrize("kind", KINDS)
def test_api_clients_get_403_for_a_private_author(kind):
	author = factories.user(is_private=True)

	r = _search(kind, f"author:{author['username']}", client=as_api(factories.api_token(factories.user())))

	assert_status(r, 403)


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("searcher", ["themselves", "admin"])
def test_private_authors_are_found_by_themselves_and_admins(kind, searcher):
	author = factories.user(is_private=True)
	item = KINDS[kind](author=author)
	client = as_user(author if searcher == "themselves" else factories.admin(2))

	r = _search(kind, f"author:{author['username']}", client=client)

	assert_in_payload(r, item["sentinel"])


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("value", ["yes", "no"])
def test_over18_keeps_only_18_plus_items(kind, value):
	adult = KINDS[kind]("zebra", over_18=True)
	other = KINDS[kind]("zebra")

	r = _search(kind, f"zebra over18:{value}")

	assert_in_payload(r, adult["sentinel"])
	assert_not_in_payload(r, other["sentinel"])


@pytest.mark.parametrize("url", ["https://example.com", "https://example.com/a/b", "https://www.example.com/x", "https://old.example.com", "https://EXAMPLE.com/y"])
def test_domain_keeps_links_to_the_domain(url):
	post = _post(url=url)

	r = _search("posts", "domain:example.com")

	assert_in_payload(r, post["sentinel"])


@pytest.mark.parametrize("url", ["https://example.org/x", "https://sub.example.com/x", "https://example.com.evil.net/x", "https://notexample.com/x"])
def test_domain_leaves_out_other_links(url):
	post = _post(url=url)

	r = _search("posts", "domain:example.com")

	assert_not_in_payload(r, post["sentinel"])


@pytest.mark.parametrize("kind", KINDS)
def test_newest_first_by_default(kind):
	older = KINDS[kind]("zebra", created_utc=NOW - 7200)
	newer = KINDS[kind]("zebra", created_utc=NOW - 60)

	r = _search(kind, "zebra")

	assert_in_order(r, [newer["sentinel"], older["sentinel"]])


@pytest.mark.parametrize("kind", KINDS)
def test_sort_and_time_filter_apply(kind):
	popular = KINDS[kind]("zebra", upvotes=9, created_utc=NOW - 7200)
	unpopular = KINDS[kind]("zebra", upvotes=1, created_utc=NOW - 60)
	too_old = KINDS[kind]("zebra", upvotes=50, created_utc=NOW - 2 * 86400)

	r = _search(kind, "zebra", sort="top", t="day")

	assert_in_order(r, [popular["sentinel"], unpopular["sentinel"]])
	assert_not_in_payload(r, too_old["sentinel"])


@pytest.mark.parametrize("kind", KINDS)
def test_sort_and_time_filter_ignore_letter_case(kind):
	popular = KINDS[kind]("zebra", upvotes=9, created_utc=NOW - 7200)
	unpopular = KINDS[kind]("zebra", upvotes=1, created_utc=NOW - 60)
	too_old = KINDS[kind]("zebra", upvotes=50, created_utc=NOW - 2 * 86400)

	r = _search(kind, "zebra", sort="TOP", t="Day")

	assert_in_order(r, [popular["sentinel"], unpopular["sentinel"]])
	assert_not_in_payload(r, too_old["sentinel"])


@pytest.mark.parametrize("kind", KINDS)
def test_pages_hold_25(kind):
	items = [KINDS[kind]("zebra", created_utc=NOW - 60 * (i + 1)) for i in range(26)]
	client = as_user(factories.user())

	first, second = _search(kind, "zebra", client=client), _search(kind, "zebra", client=client, page=2)

	assert_in_payload(first, items[24]["sentinel"])
	assert_not_in_payload(first, items[25]["sentinel"])
	assert_in_payload(second, items[25]["sentinel"])
	assert_not_in_payload(second, items[24]["sentinel"])


@pytest.mark.parametrize("kind", KINDS)
def test_api_clients_get_the_total_and_the_page(kind):
	items = [KINDS[kind]("zebra", created_utc=NOW - 60 * (i + 1)) for i in range(26)]
	KINDS[kind]("giraffe")

	r = _search(kind, "zebra", client=as_api(factories.api_token(factories.user())))

	assert_status(r, 200)
	assert set(r.json) == {"total", "data"}
	assert r.json["total"] == 26
	assert [x["id"] for x in r.json["data"]] == [x["id"] for x in items[:25]]


@pytest.mark.parametrize("kind", KINDS)
def test_the_total_counts_only_what_the_searcher_may_find(kind):
	listed = KINDS[kind]("zebra")
	KINDS[kind]("zebra", author=factories.user(shadowbanned="somemod"))
	KINDS[kind]("zebra", state_mod="REMOVED", state_mod_set_by="somemod")

	r = _search(kind, "zebra", client=as_api(factories.api_token(factories.user())))

	assert r.json["total"] == 1
	assert [x["id"] for x in r.json["data"]] == [listed["id"]]


# User search

def _user(name_part, **overrides):
	return factories.user(username=f"{name_part}{factories.unique('u')}", **overrides)


def test_users_whose_names_contain_the_query_in_any_case():
	match = _user("Zebra")
	other = _user("giraffe")

	r = as_user(factories.user()).get("/search/users", params={"q": "zEBr"})

	assert_in_payload(r, match["username"])
	assert_not_in_payload(r, other["username"])


def test_a_leading_at_sign_is_ignored():
	match = _user("zebra")

	r = as_user(factories.user()).get("/search/users", params={"q": "@zebra"})

	assert_in_payload(r, match["username"])


def test_an_exact_match_comes_first_then_most_followed():
	name = f"zebra{factories.unique('u')}"
	less = factories.user(username=f"{name}less", stored_subscriber_count=5)
	popular = factories.user(username=f"{name}popular", stored_subscriber_count=100)
	exact = factories.user(username=name)

	r = as_user(factories.user()).get("/search/users", params={"q": exact["username"].upper()})

	assert_in_order(r, [f"/@{exact['username']}\"", f"/@{popular['username']}\"", f"/@{less['username']}\""])


def test_user_pages_hold_25():
	users = [_user("zebra", stored_subscriber_count=100 - i) for i in range(26)]
	client = as_user(factories.user())

	first = client.get("/search/users", params={"q": "zebra"})
	second = client.get("/search/users", params={"q": "zebra", "page": 2})

	assert_in_payload(first, f"/@{users[24]['username']}\"")
	assert_not_in_payload(first, f"/@{users[25]['username']}\"")
	assert_in_payload(second, f"/@{users[25]['username']}\"")


def test_api_clients_get_users_as_json():
	match = _user("zebra")

	r = as_api(factories.api_token(factories.user())).get("/search/users", params={"q": match["username"]})

	assert_status(r, 200)
	assert set(r.json) == {"data"}
	assert [u["id"] for u in r.json["data"]] == [match["id"]]
