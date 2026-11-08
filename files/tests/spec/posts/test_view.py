'''
The post page: GET /post/<id> and /post/<id>/<anything> (the trailing segment is a cosmetic slug and is ignored). Query parameter "sort" orders the comments (default: the viewer's comment sort preference, "new" for visitors). API clients get the post as JSON.
'''
from urllib.parse import parse_qs, urlsplit

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


@pytest.mark.parametrize("viewer", ["visitor", "user", "api"])
def test_links_to_old_reddit_comments_ask_for_their_context(viewer):
	url = "https://old.reddit.com/r/sub/comments/abc/title/def/"
	post = factories.post(factories.user(), url=url)
	client = {"visitor": anon, "user": lambda: as_user(factories.user()), "api": lambda: as_api(factories.api_token(factories.user()))}[viewer]()

	r = _page(client, post)

	linked = r.json["url"] if viewer == "api" else next(u for u in urls_in(r.text) if u.startswith(url))
	assert parse_qs(urlsplit(linked).query).get("context")


def test_stored_links_that_are_not_web_addresses_are_not_linked():
	post = factories.post(factories.user(), url="javascript:alert(1)")

	r = _page(anon(), post)

	assert_html(r, 200)
	assert_not_in_payload(r, "javascript:alert")


# Drafts

@pytest.mark.parametrize("viewer", ["author", "moderator"])
def test_drafts_are_shown_to_their_author_and_moderators(viewer):
	author = factories.user()
	body = factories.unique("body")
	draft = factories.post(author, body=body, private=True)

	r = _page(as_user(author if viewer == "author" else factories.admin(2)), draft)

	assert_html(r, 200)
	assert_in_payload(r, body)


@pytest.mark.parametrize("viewer", ["visitor", "user", "helper", "api"])
def test_drafts_are_not_found_by_anyone_else(viewer):
	draft = factories.post(factories.user(), private=True)
	client = {"visitor": anon, "user": lambda: as_user(factories.user()), "helper": lambda: as_user(factories.admin(1)), "api": lambda: as_api(factories.api_token(factories.user()))}[viewer]()

	assert_status(_page(client, draft), 404)


# Posts embedding another post by its id (stored by earlier versions as the embed)

@pytest.mark.parametrize("viewer", ["author", "moderator"])
def test_an_embedded_draft_shows_to_its_author_and_moderators(viewer):
	author = factories.user()
	title = factories.unique("title")
	draft = factories.post(author, title=title, private=True)
	post = factories.post(factories.user(), embed_url=str(draft["id"]))

	r = _page(as_user(author if viewer == "author" else factories.admin(2)), post)

	assert_html(r, 200)
	assert_in_payload(r, title)


@pytest.mark.parametrize("viewer", ["visitor", "user"])
def test_an_embedded_draft_shows_to_no_one_else(viewer):
	title = factories.unique("title")
	draft = factories.post(factories.user(), title=title, private=True)
	post = factories.post(factories.user(), embed_url=str(draft["id"]))

	r = _page(anon() if viewer == "visitor" else as_user(factories.user()), post)

	assert_html(r, 200)
	assert_not_in_payload(r, title)


def test_comment_links_through_another_post_are_not_found():
	draft = factories.post(factories.user(), private=True)
	comment = factories.comment(factories.user(), draft)
	public = factories.post(factories.user())

	assert_status(anon().get(f"/post/{public['id']}/slug/{comment['id']}"), 404)


def test_comment_links_into_drafts_are_not_found():
	draft = factories.post(factories.user(), private=True)
	comment = factories.comment(factories.user(), draft)

	assert_status(anon().get(f"/post/{draft['id']}/slug/{comment['id']}"), 404)
	assert_status(anon().get(f"/comment/{comment['id']}"), 404)


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


# Hidden posts

def _hidden_post_content(author, **state):
	'''A link post whose every piece of content is a distinct sentinel.'''
	content = {
		"body": factories.unique("body"),
		"url": f"https://example.com/{factories.unique('link')}",
		"thumburl": f"https://example.com/{factories.unique('thumb')}.png",
		"embed_url": f"<blockquote>{factories.unique('embed')}</blockquote>",
	}
	post = factories.post(author, title=factories.unique("title"), **content, **state)
	return post, content


def _assert_content_hidden(r, post, content):
	assert_html(r, 200)
	assert_in_payload(r, post["title"])
	for sentinel in [content["body"], content["url"], content["thumburl"], content["embed_url"]]:
		assert_not_in_payload(r, sentinel.removeprefix("<blockquote>").removesuffix("</blockquote>"))


def _assert_content_shown(r, content):
	assert_html(r, 200)
	assert_in_payload(r, content["body"])
	assert_in_payload(r, content["url"])


_HIDDEN_STATES = {
	"removed": {"state_mod": "REMOVED"},
	"filtered": {"state_mod": "FILTERED"},
	"deleted": {"state_user_deleted_utc": "2020-01-01T00:00:00Z"},
}


@pytest.mark.parametrize("state", list(_HIDDEN_STATES))
@pytest.mark.parametrize("viewer", ["visitor", "user"])
def test_removed_filtered_and_deleted_posts_hide_their_content(state, viewer):
	post, content = _hidden_post_content(factories.user(), **_HIDDEN_STATES[state])

	_assert_content_hidden(_page(anon() if viewer == "visitor" else as_user(factories.user()), post), post, content)


@pytest.mark.parametrize("state", list(_HIDDEN_STATES))
@pytest.mark.parametrize("viewer", ["author", "moderator"])
def test_removed_filtered_and_deleted_posts_show_their_content_to_the_author_and_moderators(state, viewer):
	author = factories.user()
	post, content = _hidden_post_content(author, **_HIDDEN_STATES[state])

	_assert_content_shown(_page(as_user(author if viewer == "author" else factories.admin(2)), post), content)


@pytest.mark.parametrize("viewer", ["visitor", "user", "helper"])
def test_posts_by_shadowbanned_users_hide_their_content(viewer):
	post, content = _hidden_post_content(factories.user(shadowbanned="somemod"))
	client = {"visitor": anon, "user": lambda: as_user(factories.user()), "helper": lambda: as_user(factories.admin(1))}[viewer]()

	_assert_content_hidden(_page(client, post), post, content)


@pytest.mark.parametrize("removed", [False, True])
def test_a_shadowbanned_users_post_names_a_moderator_only_if_they_removed_it(removed):
	moderator = factories.unique("mod")
	post = factories.post(factories.user(shadowbanned="somemod"), state_mod="REMOVED" if removed else "VISIBLE", state_mod_set_by=moderator)

	r = _page(anon(), post)

	assert_html(r, 200)
	(assert_in_payload if removed else assert_not_in_payload)(r, moderator)


@pytest.mark.parametrize("viewer", ["author", "moderator"])
def test_posts_by_shadowbanned_users_show_their_content_to_them_and_moderators(viewer):
	author = factories.user(shadowbanned="somemod")
	post, content = _hidden_post_content(author)

	_assert_content_shown(_page(as_user(author if viewer == "author" else factories.admin(2)), post), content)


@pytest.mark.parametrize("viewer_level", [0, 1])
def test_posts_by_users_you_block_hide_their_content(viewer_level):
	author = factories.user()
	post, content = _hidden_post_content(author)
	viewer = factories.admin(viewer_level)
	db.insert("userblocks", user_id=viewer["id"], target_id=author["id"])

	_assert_content_hidden(_page(as_user(viewer), post), post, content)


@pytest.mark.parametrize("viewer_level", [2, 3])
def test_posts_by_users_admins_block_show_them_their_content(viewer_level):
	author = factories.user()
	post, content = _hidden_post_content(author)
	viewer = factories.admin(viewer_level)
	db.insert("userblocks", user_id=viewer["id"], target_id=author["id"])

	_assert_content_shown(_page(as_user(viewer), post), content)


def test_posts_by_users_who_block_you_show_their_content():
	author = factories.user()
	post, content = _hidden_post_content(author)
	viewer = factories.user()
	db.insert("userblocks", user_id=author["id"], target_id=viewer["id"])

	_assert_content_shown(_page(as_user(viewer), post), content)


@pytest.mark.parametrize("state", list(_HIDDEN_STATES))
def test_comment_links_into_hidden_posts_hide_the_post_content(state):
	post, content = _hidden_post_content(factories.user(), **_HIDDEN_STATES[state])
	comment = factories.comment(factories.user(), post)

	r = anon().get(f"/comment/{comment['id']}")

	_assert_content_hidden(r, post, content)
	assert_in_payload(r, comment["body"])


def test_api_json_of_a_hidden_post_has_only_its_identity():
	post, content = _hidden_post_content(factories.user(shadowbanned="somemod"))

	r = _page(as_api(factories.api_token(factories.user())), post)

	assert set(r.json) == {"state_user_deleted_utc", "state_mod_set_by", "id", "title", "permalink"}


def test_api_json_of_a_removed_post_is_complete_for_its_author():
	author = factories.user()
	post, content = _hidden_post_content(author, state_mod="REMOVED")

	r = _page(as_api(factories.api_token(author)), post)

	assert r.json["body"] == content["body"]


@pytest.mark.parametrize("state", list(_HIDDEN_STATES))
def test_comments_under_a_hidden_post_are_still_shown(state):
	post = factories.post(factories.user(), **_HIDDEN_STATES[state])
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


@pytest.mark.parametrize("sort, first_overrides", [("comments", {"descendant_count": 3}), ("controversial", {"upvotes": 5, "downvotes": 5})])
def test_sort_parameter_orders_by_replies_and_split_votes(sort, first_overrides):
	post = factories.post(factories.user())
	first = factories.comment(factories.user(), post, created_utc=1000, **first_overrides)
	second = factories.comment(factories.user(), post, created_utc=2000, upvotes=10)

	assert _order(_page(anon(), post, params={"sort": sort}), [first, second]) == [first["id"], second["id"]]


@pytest.mark.parametrize("sort", ["new", "old", "top", "bottom", "controversial", "comments"])
@pytest.mark.parametrize("replies", [False, True], ids=["top-level", "replies"])
def test_comments_made_in_the_same_second_list_the_last_made_first(sort, replies):
	post = factories.post(factories.user())
	parent = factories.comment(factories.user(), post, created_utc=500) if replies else None
	comments = [factories.comment(factories.user(), post, parent=parent, created_utc=1000) for _ in range(3)]

	assert _order(_page(anon(), post, params={"sort": sort}), comments) == [c["id"] for c in (comments if sort == "old" else comments[::-1])]
@pytest.mark.parametrize("time_order", [True, False], ids=["made in time order", "made in the opposite order"])
@pytest.mark.parametrize("replies", [False, True], ids=["top-level", "replies"])
def test_comments_with_as_many_replies_list_newest_first(replies, time_order):
	post = factories.post(factories.user())
	parent = factories.comment(factories.user(), post, created_utc=500) if replies else None
	made = [factories.comment(factories.user(), post, parent=parent, created_utc=at) for at in ((1000, 2000) if time_order else (2000, 1000))]
	older, newer = sorted(made, key=lambda c: c["created_utc"])

	assert _order(_page(anon(), post, params={"sort": "comments"}), [older, newer]) == [newer["id"], older["id"]]


@pytest.mark.parametrize("sort", ["hot", "bogus"])
def test_unknown_comment_sorts_fall_back_to_the_default(sort):
	post = factories.post(factories.user())
	older = factories.comment(factories.user(), post, created_utc=1000, upvotes=1)
	newer = factories.comment(factories.user(), post, created_utc=2000, upvotes=5)
	u = factories.user(defaultsortingcomments="old")

	assert _order(_page(as_user(u), post, params={"sort": sort}), [older, newer]) == [older["id"], newer["id"]]


def test_the_sort_parameter_is_not_echoed_into_the_page():
	marker = factories.unique("injected")
	post = factories.post(factories.user())
	big = factories.comment(factories.user(), post)
	for _ in range(200):
		factories.comment(factories.user(), post, parent=big)
	factories.comment(factories.user(), post)

	r = _page(anon(), post, params={"sort": f"');{marker}//"})

	assert_html(r, 200)
	assert_not_in_payload(r, marker)


def test_users_get_their_preferred_comment_sort_by_default():
	post, older, newer = _older_and_newer_comments()
	u = factories.user(defaultsortingcomments="old")

	assert _order(_page(as_user(u), post), [older, newer]) == [older["id"], newer["id"]]


def test_pinned_comments_come_first():
	post = factories.post(factories.user())
	pinned = factories.comment(factories.user(), post, created_utc=1000, is_pinned="somemod")
	newer = factories.comment(factories.user(), post, created_utc=2000)

	assert _order(_page(anon(), post), [pinned, newer]) == [pinned["id"], newer["id"]]


@pytest.mark.parametrize("replies", [False, True], ids=["top-level", "replies"])
def test_pinned_comments_list_newest_first_whoever_pinned_them(replies):
	post = factories.post(factories.user())
	parent = factories.comment(factories.user(), post, created_utc=500) if replies else None
	# The pinners' names sort neither way their times do
	pins = [factories.comment(factories.user(), post, parent=parent, created_utc=at, is_pinned=name) for at, name in ((1000, "m-mod"), (2000, "z-mod"), (3000, "a-mod"))]
	unpinned = factories.comment(factories.user(), post, parent=parent, created_utc=4000)

	assert _order(_page(anon(), post, params={"sort": "old"}), [*pins, unpinned]) == [pins[2]["id"], pins[1]["id"], pins[0]["id"], unpinned["id"]]


def test_the_newest_pinned_threads_fill_the_first_page_whatever_the_sort():
	post = factories.post(factories.user())
	pins = [factories.comment(factories.user(), post, created_utc=at, is_pinned=name) for at, name in ((1000, "m-mod"), (2000, "a-mod"), (3000, "z-mod"))]
	for pin in pins:
		for _ in range(100):
			factories.comment(factories.user(), post, parent=pin)

	r = _page(anon(), post, params={"sort": "old"})

	# A page holds whole threads until it has 200 comments: the two newest pinned threads
	assert_html(r, 200)
	assert_not_in_payload(r, pins[0]["body"])
	assert_in_payload(r, pins[1]["body"])
	assert_in_payload(r, pins[2]["body"])


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
