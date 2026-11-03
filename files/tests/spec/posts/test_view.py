'''
The post page: GET /post/<id> and /post/<id>/<anything> (the trailing segment is a cosmetic slug and is ignored). Query parameter "sort" orders the comments (default: the viewer's comment sort preference, "new" for visitors). API clients get the post as JSON.
'''
import pytest

from files.tests.spec.harness import *


def _page(client, post, **kwargs):
	return client.get(f"/post/{post['id']}", **kwargs)


def test_visitors_see_the_post():
	title, body = factories.unique("title"), factories.unique("body")
	post = factories.post(factories.user(), title=title, body=body)

	r = _page(anon(), post)

	assert_html(r, 200)
	assert_in_payload(r, title)
	assert_in_payload(r, body)


def test_any_trailing_segment_shows_the_same_post():
	body = factories.unique("body")
	post = factories.post(factories.user(), body=body)

	r = anon().get(f"/post/{post['id']}/not-the-real-slug")

	assert_html(r, 200)
	assert_in_payload(r, body)


def test_each_view_is_counted():
	post = factories.post(factories.user())

	with db_diff() as d:
		_page(anon(), post)
		_page(anon(), post)

	d.assert_exactly(updated={"submissions": {post["id"]: {"views": 2}}})


@pytest.mark.parametrize("pid", ["0", "abc"])
def test_unknown_posts_are_not_found(pid):
	assert_status(anon().get(f"/post/{pid}"), 404)


def test_link_posts_show_their_link():
	url = f"https://example.com/{factories.unique('path')}"
	post = factories.post(factories.user(), url=url)

	assert_in_payload(_page(anon(), post), url)


# 18+ posts

def test_visitors_must_confirm_their_age_before_seeing_an_18_plus_post():
	body = factories.unique("body")
	post = factories.post(factories.user(), body=body, over_18=True)

	r = _page(anon(), post)

	assert_html(r, 200)
	assert_not_in_payload(r, body)


def test_confirming_age_shows_18_plus_posts_to_visitors():
	body = factories.unique("body")
	post = factories.post(factories.user(), body=body, over_18=True)
	visitor = anon()

	assert_redirect(visitor.post("/allow_nsfw", {"redir": f"/post/{post['id']}"}), f"/post/{post['id']}")
	r = _page(visitor, post)

	assert_html(r, 200)
	assert_in_payload(r, body)


def test_users_who_are_18_plus_see_18_plus_posts():
	body = factories.unique("body")
	post = factories.post(factories.user(), body=body, over_18=True)

	assert_in_payload(_page(as_user(factories.user(over_18=True)), post), body)


def test_users_who_are_not_18_plus_must_confirm_too():
	body = factories.unique("body")
	post = factories.post(factories.user(), body=body, over_18=True)

	r = _page(as_user(factories.user()), post)

	assert_html(r, 200)
	assert_not_in_payload(r, body)


def test_scripts_are_refused_18_plus_posts_without_confirmation():
	post = factories.post(factories.user(), over_18=True)

	assert_status(_page(anon(), post, headers=XHR), 403)


def test_api_clients_are_refused_18_plus_posts_unless_18_plus():
	post = factories.post(factories.user(), over_18=True)

	assert_status(_page(as_api(factories.api_token(factories.user())), post), 403)


def test_api_clients_that_are_18_plus_get_18_plus_posts():
	post = factories.post(factories.user(), over_18=True)

	r = _page(as_api(factories.api_token(factories.user(over_18=True))), post)

	assert_status(r, 200)
	assert r.json["id"] == post["id"]


# Removed posts

@pytest.mark.parametrize("state_mod", ["REMOVED", "FILTERED"])
def test_removed_and_filtered_posts_show_only_their_title_to_others(state_mod):
	title, body = factories.unique("title"), factories.unique("body")
	post = factories.post(factories.user(), title=title, body=body, state_mod=state_mod)

	for client in [anon(), as_user(factories.user()), as_user(factories.admin(1))]:
		r = _page(client, post)
		assert_html(r, 200)
		assert_in_payload(r, title)
		assert_not_in_payload(r, body)


@pytest.mark.parametrize("state_mod", ["REMOVED", "FILTERED"])
@pytest.mark.parametrize("viewer", ["author", "moderator"])
def test_removed_and_filtered_posts_stay_visible_to_their_author_and_moderators(state_mod, viewer):
	author = factories.user()
	body = factories.unique("body")
	post = factories.post(author, body=body, state_mod=state_mod)

	r = _page(as_user(author if viewer == "author" else factories.admin(2)), post)

	assert_html(r, 200)
	assert_in_payload(r, body)


def test_comments_under_a_removed_post_are_still_shown():
	post = factories.post(factories.user(), state_mod="REMOVED")
	comment = factories.comment(factories.user(), post)

	assert_in_payload(_page(anon(), post), comment["body"])


# Comments

def test_comments_and_their_replies_are_shown():
	post = factories.post(factories.user())
	top = factories.comment(factories.user(), post)
	reply = factories.comment(factories.user(), post, parent=top)

	r = _page(anon(), post)

	assert_in_payload(r, top["body"])
	assert_in_payload(r, reply["body"])


def _order(r, comments):
	positions = {c["id"]: r.text.index(c["body"]) for c in comments}
	return sorted(positions, key=positions.get)


def _older_and_newer_comments():
	post = factories.post(factories.user())
	older = factories.comment(factories.user(), post, created_utc=1000, upvotes=5)
	newer = factories.comment(factories.user(), post, created_utc=2000, upvotes=1)
	return post, older, newer


def test_visitors_see_newest_comments_first():
	post, older, newer = _older_and_newer_comments()

	assert _order(_page(anon(), post), [older, newer]) == [newer["id"], older["id"]]


@pytest.mark.parametrize("sort, first", [("old", "older"), ("new", "newer"), ("top", "older"), ("bottom", "newer")])
def test_sort_parameter_orders_comments(sort, first):
	post, older, newer = _older_and_newer_comments()

	order = _order(_page(anon(), post, params={"sort": sort}), [older, newer])

	assert order[0] == (older if first == "older" else newer)["id"]


def test_users_get_their_preferred_comment_sort_by_default():
	post, older, newer = _older_and_newer_comments()
	u = factories.user(defaultsortingcomments="old")

	assert _order(_page(as_user(u), post), [older, newer]) == [older["id"], newer["id"]]


def test_pinned_comments_come_first():
	post = factories.post(factories.user())
	pinned = factories.comment(factories.user(), post, created_utc=1000, is_pinned="somemod")
	newer = factories.comment(factories.user(), post, created_utc=2000)

	assert _order(_page(anon(), post), [pinned, newer]) == [pinned["id"], newer["id"]]


def test_comments_beyond_the_first_page_are_left_for_view_more():
	'''A page holds whole top-level threads until it has 200 or more comments; later threads are fetched with /viewmore.'''
	post = factories.post(factories.user())
	big = factories.comment(factories.user(), post, created_utc=2000)
	for _ in range(199):
		factories.comment(factories.user(), post, parent=big)
	later = factories.comment(factories.user(), post, created_utc=1000)

	r = _page(anon(), post)

	assert_in_payload(r, big["body"])
	assert_not_in_payload(r, later["body"])


def test_a_page_fits_threads_until_it_reaches_200_comments():
	post = factories.post(factories.user())
	big = factories.comment(factories.user(), post, created_utc=2000)
	for _ in range(198):
		factories.comment(factories.user(), post, parent=big)
	later = factories.comment(factories.user(), post, created_utc=1000)

	assert_in_payload(_page(anon(), post), later["body"])


# API

def test_api_clients_get_the_post_as_json():
	author = factories.user()
	post = factories.post(author, body="hello", url="https://example.com/x", created_utc=1000)
	reader = factories.user()

	r = _page(as_api(factories.api_token(reader)), post)

	assert_status(r, 200)
	assert r.json == {
		"author_name": author["username"],
		"permalink": f"http://{config.site_host()}/post/{post['id']}/{post['title']}",
		"shortlink": f"/post/{post['id']}/{post['title']}",
		"created_utc": 1000,
		"id": post["id"],
		"title": post["title"],
		"is_nsfw": False,
		"is_bot": False,
		"thumb_url": ANY,
		"domain": "example.com",
		"url": "https://example.com/x",
		"body": "hello",
		"body_html": "<p>hello</p>",
		"edited_utc": 0,
		"comment_count": 0,
		"stickied": None,
		"private": False,
		"distinguish_level": 0,
		"voted": 0,
		"score": 1,
		"upvotes": 1,
		"downvotes": 0,
		"author": ANY,
		"replies": [],
	}
	assert r.json["author"]["id"] == author["id"]


def test_api_json_includes_top_level_comments():
	post = factories.post(factories.user())
	top = factories.comment(factories.user(), post)
	factories.comment(factories.user(), post, parent=top)

	r = _page(as_api(factories.api_token(factories.user())), post)

	assert [c["id"] for c in r.json["replies"]] == [top["id"]]


def test_api_json_hides_scores_of_young_posts():
	post = factories.post(factories.user())

	r = _page(as_api(factories.api_token(factories.user())), post)

	assert not {"score", "upvotes", "downvotes"} & set(r.json)


def test_api_json_of_a_removed_post_has_only_its_identity():
	post = factories.post(factories.user(), state_mod="REMOVED", state_mod_set_by="somemod", created_utc=1000)

	r = _page(as_api(factories.api_token(factories.user())), post)

	assert r.json == {
		"state_user_deleted_utc": None,
		"state_mod_set_by": "somemod",
		"id": post["id"],
		"title": post["title"],
		"permalink": ANY,
	}
