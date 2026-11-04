'''
Profile pages: GET /@<username>/posts lists the user's posts, GET /@<username>/ their comments on posts (not their private messages). Both find the user by their username or the username they signed up with, ignoring letter case; a name that isn't exactly the current username redirects (302) to the same page under it. An unknown name is 404.

Before listing anything:
- A reserved name (an account held for someone) shows a page naming who it's reserved for; script (xhr) and API clients are refused with 403.
- A private profile shows only its owner and admins (level 2 and up) the listings; anyone else gets a page without them, or 403 as a script or API client.
- A viewer who blocks the user gets a page saying so instead of the listings, or 403 as a script or API client, whether or not the user blocks them too. Being blocked by the user changes nothing.

The listings hold 25 items to a page, with "page" (from 1; anything else means 1) choosing the page. "sort" orders them: new (the default: newest first), old, top (highest score first), bottom, comments (most comments first; for comments, most replies), controversial (closest to evenly split votes first), hot (score weighed against age), and for posts bump (most recently bumped first, among posts with more than one comment). "t" (hour, day, week, month, year; anything else means all time) keeps only items created within that long. Ties fall back to newest first.

What's listed depends on the viewer. Everyone sees the user's visible posts and comments; the user themselves and admins (level 2 and up) also see the deleted, removed, held ("filtered") and anonymous ("ghost") ones, and the user's unpublished drafts. Nobody else sees anything of a shadowbanned user, other shadowbanned users included. The user's pinned posts lead the first page of their posts.

API clients get the listing as JSON: an object whose "data" is the list of items.
'''
import time

import pytest

from files.tests.spec.harness import *

PAGES = ["posts", "comments"]

VIEWERS = ["anonymous", "other user", "owner", "admin"]


def _path(user, page):
	return f"/@{user['username']}/posts" if page == "posts" else f"/@{user['username']}/"


def _client(viewer, owner):
	if viewer == "anonymous":
		return anon()
	if viewer == "owner":
		return as_user(owner)
	if viewer == "admin":
		return as_user(factories.admin(2))
	return as_user(factories.user())


def _item(user, page, **overrides):
	'''A post (for the posts page) or a comment on someone's post (for the comments page) by `user`; returns its sentinel.'''
	token = factories.unique()
	if page == "posts":
		factories.post(user, title=token, **overrides)
	else:
		factories.comment(user, factories.post(factories.user()), body=token, **overrides)
	return token


def _item_row(user, page, **overrides):
	token = factories.unique()
	if page == "posts":
		return factories.post(user, title=token, **overrides), token
	return factories.comment(user, factories.post(factories.user()), body=token, **overrides), token


# Finding the user

@pytest.mark.parametrize("page", PAGES)
def test_profile_lists_the_users_items(page):
	user = factories.user()
	token = _item(user, page)

	r = anon().get(_path(user, page))

	assert_html(r, 200)
	assert_in_payload(r, token)


@pytest.mark.parametrize("page", PAGES)
def test_profile_of_an_unknown_user_is_not_found(page):
	r = anon().get(_path({"username": factories.unique()}, page))

	assert_status(r, 404)


@pytest.mark.parametrize("page", PAGES)
def test_profile_under_another_letter_case_redirects_to_the_username(page):
	user = factories.user(username=f"Mixed{factories.unique()}")

	r = anon().get(_path({"username": user["username"].upper()}, page))

	assert_redirect(r, _path(user, page))


@pytest.mark.parametrize("page", PAGES)
def test_profile_under_the_original_username_redirects_to_the_current_one(page):
	original = factories.unique("old")
	user = factories.user(original_username=original)

	r = anon().get(_path({"username": original}, page))

	assert_redirect(r, _path(user, page))


# Reserved names

@pytest.mark.parametrize("page", PAGES)
def test_reserved_profile_names_who_its_for(page):
	holder = factories.unique()
	user = factories.user(reserved=holder)

	r = anon().get(_path(user, page))

	assert_html(r, 200)
	assert_in_payload(r, holder)


@pytest.mark.parametrize("page", PAGES)
def test_reserved_profile_refuses_scripts(page):
	user = factories.user(reserved=factories.unique())

	r = anon().get(_path(user, page), headers=XHR)

	assert_status(r, 403)


@pytest.mark.parametrize("page", PAGES)
def test_reserved_profile_refuses_api_clients(page):
	user = factories.user(reserved=factories.unique())

	r = as_api(factories.api_token(factories.user())).get(_path(user, page))

	assert_status(r, 403)


# Private profiles

@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("viewer", ["anonymous", "other user"])
def test_private_profile_hides_its_listing(page, viewer):
	user = factories.user(is_private=True)
	token = _item(user, page)

	r = _client(viewer, user).get(_path(user, page))

	assert_html(r, 200)
	assert_not_in_payload(r, token)


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("viewer", ["owner", "admin"])
def test_private_profile_shows_its_listing_to_the_owner_and_admins(page, viewer):
	user = factories.user(is_private=True)
	token = _item(user, page)

	r = _client(viewer, user).get(_path(user, page))

	assert_html(r, 200)
	assert_in_payload(r, token)


@pytest.mark.parametrize("page", PAGES)
def test_private_profile_refuses_scripts(page):
	user = factories.user(is_private=True)

	r = as_user(factories.user()).get(_path(user, page), headers=XHR)

	assert_status(r, 403)


@pytest.mark.parametrize("page", PAGES)
def test_private_profile_refuses_api_clients(page):
	user = factories.user(is_private=True)

	r = as_api(factories.api_token(factories.user())).get(_path(user, page))

	assert_status(r, 403)


# Blocks

@pytest.mark.parametrize("page", PAGES)
def test_profile_of_a_user_you_block_hides_its_listing(page):
	user, viewer = factories.user(), factories.user()
	token = _item(user, page)
	db.insert("userblocks", user_id=viewer["id"], target_id=user["id"])

	r = as_user(viewer).get(_path(user, page))

	assert_html(r, 200)
	assert_not_in_payload(r, token)


@pytest.mark.parametrize("page", PAGES)
def test_profile_of_a_user_you_block_refuses_scripts(page):
	user, viewer = factories.user(), factories.user()
	db.insert("userblocks", user_id=viewer["id"], target_id=user["id"])

	r = as_user(viewer).get(_path(user, page), headers=XHR)

	assert_status(r, 403)


@pytest.mark.parametrize("page", PAGES)
def test_profile_of_a_user_blocking_you_still_lists(page):
	user, viewer = factories.user(), factories.user()
	token = _item(user, page)
	db.insert("userblocks", user_id=user["id"], target_id=viewer["id"])

	r = as_user(viewer).get(_path(user, page))

	assert_html(r, 200)
	assert_in_payload(r, token)


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("theirs_first", [False, True], ids=["yours first", "theirs first"])
def test_profile_of_a_user_you_block_hides_its_listing_though_they_block_you_too(page, theirs_first):
	user, viewer = factories.user(), factories.user()
	token = _item(user, page)
	blocks = [dict(user_id=viewer["id"], target_id=user["id"]), dict(user_id=user["id"], target_id=viewer["id"])]
	for block in reversed(blocks) if theirs_first else blocks:
		db.insert("userblocks", **block)

	r = as_user(viewer).get(_path(user, page))

	assert_html(r, 200)
	assert_not_in_payload(r, token)


# What's listed, by viewer

HIDDEN_POSTS = {
	"deleted": {"state_user_deleted_utc": "2020-01-01T00:00:00Z"},
	"removed": {"state_mod": "REMOVED"},
	"filtered": {"state_mod": "FILTERED"},
	"draft": {"private": True},
	"ghost": {"ghost": True},
}

HIDDEN_COMMENTS = {
	"deleted": {"state_user_deleted_utc": "2020-01-01T00:00:00Z"},
	"removed": {"state_mod": "REMOVED"},
	"filtered": {"state_mod": "FILTERED"},
	"ghost": {"ghost": True},
}


def _hidden_cases(shown: bool):
	viewers = ["owner", "admin"] if shown else ["anonymous", "other user"]
	return [pytest.param("posts", state, viewer, id=f"posts-{state}-{viewer}") for state in HIDDEN_POSTS for viewer in viewers] + [pytest.param("comments", state, viewer, id=f"comments-{state}-{viewer}") for state in HIDDEN_COMMENTS for viewer in viewers]


@pytest.mark.parametrize("page, state, viewer", _hidden_cases(shown=False))
def test_profile_hides_hidden_items_from_others(page, state, viewer):
	user = factories.user()
	token = _item(user, page, **(HIDDEN_POSTS if page == "posts" else HIDDEN_COMMENTS)[state])

	r = _client(viewer, user).get(_path(user, page))

	assert_html(r, 200)
	assert_not_in_payload(r, token)


@pytest.mark.parametrize("page, state, viewer", _hidden_cases(shown=True))
def test_profile_shows_hidden_items_to_the_owner_and_admins(page, state, viewer):
	user = factories.user()
	token = _item(user, page, **(HIDDEN_POSTS if page == "posts" else HIDDEN_COMMENTS)[state])

	r = _client(viewer, user).get(_path(user, page))

	assert_html(r, 200)
	assert_in_payload(r, token)


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("viewer", ["anonymous", "other user"])
def test_profile_of_a_shadowbanned_user_lists_nothing_to_others(page, viewer):
	user = factories.user(shadowbanned="somemod")
	token = _item(user, page)

	r = _client(viewer, user).get(_path(user, page))

	assert_html(r, 200)
	assert_not_in_payload(r, token)


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("viewer", ["owner", "admin"])
def test_profile_of_a_shadowbanned_user_lists_to_themselves_and_admins(page, viewer):
	user = factories.user(shadowbanned="somemod")
	token = _item(user, page)

	r = _client(viewer, user).get(_path(user, page))

	assert_html(r, 200)
	assert_in_payload(r, token)


@pytest.mark.parametrize("page", PAGES)
def test_profile_of_a_shadowbanned_user_lists_nothing_to_other_shadowbanned_users(page):
	user = factories.user(shadowbanned="somemod")
	token = _item(user, page)

	r = as_user(factories.user(shadowbanned="somemod")).get(_path(user, page))

	assert_html(r, 200)
	assert_not_in_payload(r, token)


def test_profile_comments_leave_out_private_messages():
	user, recipient = factories.user(), factories.user()
	token = factories.unique()
	message_id = db.execute("SELECT nextval('comments_id_seq')")
	db.insert("comments", id=message_id, author_id=user["id"], parent_submission=None, sentto=recipient["id"], level=1, top_comment_id=message_id, created_utc=int(time.time()), body=token, body_html=f"<p>{token}</p>", volunteer_janitor_badness=0.5, state_mod="VISIBLE", state_report="UNREPORTED")
	listed = _item(user, "comments")

	r = as_user(user).get(_path(user, "comments"))

	assert_html(r, 200)
	assert_in_payload(r, listed)
	assert_not_in_payload(r, token)


# Paging

@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("number", [1, 2])
def test_profile_pages_hold_25_items(page, number):
	user = factories.user()
	oldest, *rest = [_item(user, page, created_utc=1_700_000_000 + i) for i in range(26)]

	r = anon().get(_path(user, page), params={"page": number})

	assert_html(r, 200)
	on_page, off_page = (rest, [oldest]) if number == 1 else ([oldest], rest)
	for token in on_page:
		assert_in_payload(r, token)
	for token in off_page:
		assert_not_in_payload(r, token)


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("number", ["0", "-2", "x"])
def test_profile_invalid_page_shows_the_first(page, number):
	user = factories.user()
	oldest, *rest = [_item(user, page, created_utc=1_700_000_000 + i) for i in range(26)]

	r = anon().get(_path(user, page), params={"page": number})

	assert_html(r, 200)
	assert_in_payload(r, rest[-1])
	assert_not_in_payload(r, oldest)


# Sorting: each case makes the older item come first, which the default order never does

NOW = int(time.time())

SORTS = {
	"old": ({}, {}),
	"top": ({"upvotes": 5}, {"upvotes": 2}),
	"bottom": ({"upvotes": 1, "downvotes": 3}, {"upvotes": 2}),
	"controversial": ({"upvotes": 5, "downvotes": 5}, {"upvotes": 10}),
	"hot": ({"upvotes": 1000, "created_utc": NOW - 3600}, {"upvotes": 1, "created_utc": NOW}),
}

POST_SORTS = {
	**SORTS,
	"comments": ({"comment_count": 5}, {"comment_count": 2}),
	"bump": ({"comment_count": 2, "bump_utc": NOW}, {"comment_count": 2, "bump_utc": NOW - 100}),
}

COMMENT_SORTS = {
	**SORTS,
	"comments": ({"descendant_count": 5}, {"descendant_count": 2}),
}


def _sort_cases():
	return [pytest.param("posts", sort, id=f"posts-{sort}") for sort in POST_SORTS] + [pytest.param("comments", sort, id=f"comments-{sort}") for sort in COMMENT_SORTS]


@pytest.mark.parametrize("page, sort", _sort_cases())
def test_profile_sorts(page, sort):
	user = factories.user()
	first_overrides, second_overrides = (POST_SORTS if page == "posts" else COMMENT_SORTS)[sort]
	first = _item(user, page, **{"created_utc": NOW - 7200, **first_overrides})
	second = _item(user, page, **{"created_utc": NOW - 60, **second_overrides})

	r = anon().get(_path(user, page), params={"sort": sort})

	assert_html(r, 200)
	assert r.text.index(first) < r.text.index(second)


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("sort", ["new", "nonsense"])
def test_profile_lists_newest_first_by_default(page, sort):
	user = factories.user()
	older = _item(user, page, created_utc=NOW - 7200)
	newer = _item(user, page, created_utc=NOW - 60)

	r = anon().get(_path(user, page), params={"sort": sort})

	assert_html(r, 200)
	assert r.text.index(newer) < r.text.index(older)


def test_profile_bump_sort_lists_only_posts_with_more_than_one_comment():
	user = factories.user()
	listed = _item(user, "posts", comment_count=2)
	token = _item(user, "posts", comment_count=1)

	r = anon().get(_path(user, "posts"), params={"sort": "bump"})

	assert_html(r, 200)
	assert_in_payload(r, listed)
	assert_not_in_payload(r, token)


TIMES = [
	("hour", 30 * 60, 2 * 3600),
	("day", 2 * 3600, 2 * 86400),
	("week", 2 * 86400, 8 * 86400),
	("month", 8 * 86400, 31 * 86400),
	("year", 31 * 86400, 366 * 86400),
]


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("t, inside, outside", TIMES, ids=[t for t, _, _ in TIMES])
def test_profile_time_filter(page, t, inside, outside):
	user = factories.user()
	listed = _item(user, page, created_utc=int(time.time()) - inside)
	token = _item(user, page, created_utc=int(time.time()) - outside)

	r = anon().get(_path(user, page), params={"t": t})

	assert_html(r, 200)
	assert_in_payload(r, listed)
	assert_not_in_payload(r, token)


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("t", ["all", "nonsense"])
def test_profile_time_filter_all(page, t):
	user = factories.user()
	token = _item(user, page, created_utc=int(time.time()) - 10 * 366 * 86400)

	r = anon().get(_path(user, page), params={"t": t})

	assert_html(r, 200)
	assert_in_payload(r, token)


# Pins

@pytest.mark.parametrize("number", [1, 2])
def test_pinned_post_leads_the_first_page_only(number):
	user = factories.user()
	pinned = _item(user, "posts", is_pinned=True, created_utc=1_600_000_000)
	oldest, *rest = [_item(user, "posts", created_utc=1_700_000_000 + i) for i in range(26)]

	r = anon().get(_path(user, "posts"), params={"page": number})

	assert_html(r, 200)
	if number == 1:
		assert r.text.index(pinned) < r.text.index(rest[-1])
		assert_not_in_payload(r, oldest)
	else:
		assert_not_in_payload(r, pinned)
		assert_in_payload(r, oldest)


# API clients

@pytest.mark.parametrize("page", PAGES)
def test_profile_answers_api_clients_with_json(page):
	user = factories.user()
	older, _ = _item_row(user, page, created_utc=NOW - 7200)
	newer, _ = _item_row(user, page, created_utc=NOW - 60)

	r = as_api(factories.api_token(factories.user())).get(_path(user, page))

	assert_status(r, 200)
	assert set(r.json) == {"data"}
	assert [item["id"] for item in r.json["data"]] == [newer["id"], older["id"]]
