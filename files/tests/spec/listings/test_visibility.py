'''
Which posts and comments the listings show to whom: the front page (GET /, its pinned posts alike), post search (GET /search/posts), the comment listing (GET /comments) and comment search (GET /search/comments). /changelog and random picks are in their own files.

- Posts and comments that moderators removed or filtered are shown only to their authors and to admins from level 2.
- Items their authors deleted, and drafts, are left out of the front page for everyone; post and comment search show them only to admins from level 2. Comments on drafts likewise.
- Items by a shadowbanned user are left out for everyone but their author (who sees their own) and admins from level 2. Other shadowbanned users don't see them either.
- Items by a user the viewer blocks are left out, even distinguished ones, except for admins from level 2. Items by users who block the viewer are listed.
- Private messages are never listed as comments.
- API clients see what a user without admin rights sees, whatever their account's level.

Each table below maps (state, viewer) to whether the item is listed.
'''
import pytest

from files.tests.spec.harness import *

POST_STATES = {
	"removed": {"state_mod": "REMOVED", "state_mod_set_by": "somemod"},
	"filtered": {"state_mod": "FILTERED"},
	"deleted": {"state_user_deleted_utc": "2020-01-01T00:00:00Z"},
	"draft": {"private": True},
}
COMMENT_STATES = {k: v for k, v in POST_STATES.items() if k != "draft"}

FRONT = {
	**{(state, "visitor"): False for state in POST_STATES},
	**{(state, "user"): False for state in POST_STATES},
	**{(state, "admin token"): False for state in POST_STATES},
	("removed", "author"): True, ("filtered", "author"): True, ("deleted", "author"): False, ("draft", "author"): False,
	("removed", "admin"): True, ("filtered", "admin"): True, ("deleted", "admin"): False, ("draft", "admin"): False,
	("shadowbanned author", "visitor"): False, ("shadowbanned author", "user"): False, ("shadowbanned author", "author"): True,
	("shadowbanned author", "shadowbanned user"): False, ("shadowbanned author", "admin"): True, ("shadowbanned author", "admin token"): False,
	("blocked author", "user"): False, ("blocked author", "admin"): True, ("blocked author", "admin token"): False,
	("blocked distinguished author", "user"): False,
	("author blocking the viewer", "user"): True,
}

SEARCH_POSTS = {
	**{(state, "user"): False for state in POST_STATES},
	**{(state, "admin token"): False for state in POST_STATES},
	**{(state, "admin"): True for state in POST_STATES},
	("removed", "author"): True, ("filtered", "author"): True, ("deleted", "author"): False, ("draft", "author"): False,
	("shadowbanned author", "author"): True, ("shadowbanned author", "admin"): True,
	("shadowbanned author", "user"): False, ("shadowbanned author", "shadowbanned user"): False, ("shadowbanned author", "admin token"): False,
	("blocked author", "user"): False, ("blocked author", "admin"): True,
	("blocked distinguished author", "user"): False,
	("author blocking the viewer", "user"): True,
}

COMMENTS = {
	**{(state, "user"): False for state in COMMENT_STATES},
	**{(state, "admin token"): False for state in COMMENT_STATES},
	("removed", "admin"): True, ("filtered", "admin"): True,
	("removed", "author"): True, ("filtered", "author"): True, ("deleted", "author"): False,
	("on a draft", "user"): False,
	("shadowbanned author", "user"): False, ("shadowbanned author", "admin"): True,
	("shadowbanned author", "author"): True, ("shadowbanned author", "shadowbanned user"): False,
	("blocked author", "user"): False, ("blocked author", "admin"): True,
	("blocked distinguished author", "user"): False,
	("author blocking the viewer", "user"): True,
}

SEARCH_COMMENTS = {
	**{(state, "user"): False for state in COMMENT_STATES},
	**{(state, "admin token"): False for state in COMMENT_STATES},
	**{(state, "admin"): True for state in COMMENT_STATES},
	("deleted", "author"): False,
	("on a draft", "user"): False, ("on a draft", "admin"): True,
	("shadowbanned author", "user"): False, ("shadowbanned author", "author"): True, ("shadowbanned author", "admin"): True,
	("blocked author", "user"): False, ("blocked author", "admin"): True,
	("blocked distinguished author", "user"): False,
	("author blocking the viewer", "user"): True,
}


def _cases(table):
	return [pytest.param(state, viewer, listed, id=f"{state}-{viewer}-{'listed' if listed else 'left out'}") for (state, viewer), listed in table.items()]


def _arrange(state, viewer, make_item):
	'''Makes the viewer, then the item in `state` (by a fresh author, or by the viewer when the viewer is "author"); returns (client, item).'''
	if viewer in ("admin", "admin token"):
		viewer_row = factories.admin(2)
	else:
		viewer_row = factories.user(shadowbanned="somemod" if viewer == "shadowbanned user" or (state == "shadowbanned author" and viewer == "author") else None)
	if viewer == "author":
		author = viewer_row
	else:
		author = factories.user(shadowbanned="somemod" if state == "shadowbanned author" else None)
	if state.startswith("blocked"):
		db.insert("userblocks", user_id=viewer_row["id"], target_id=author["id"])
	if state == "author blocking the viewer":
		db.insert("userblocks", user_id=author["id"], target_id=viewer_row["id"])
	overrides = dict(POST_STATES.get(state, {}))
	if state == "blocked distinguished author":
		overrides["distinguish_level"] = 1
	item = make_item(author, state, overrides)
	if viewer == "visitor":
		client = anon()
	elif viewer == "admin token":
		client = as_api(factories.api_token(viewer_row))
	else:
		client = as_user(viewer_row)
	return client, item


def _assert_listed(r, client, item, listed):
	assert_status(r, 200)
	if client.authorization:
		ids = [x["id"] for x in r.json["data"]]
		assert (item["id"] in ids) == listed, f"expected the item {'listed' if listed else 'left out'}; listed ids {ids}"
	else:
		(assert_in_payload if listed else assert_not_in_payload)(r, item["sentinel"])


# Searches look for a word of the item's text other than the sentinel asserted on, since result pages repeat the query
WORD = "zebra"


def _post_in(author, state, overrides):
	sentinel = factories.unique()
	return {**factories.post(author, title=f"{WORD} {sentinel}", **overrides), "sentinel": sentinel}


def _comment_in(author, state, overrides):
	post = factories.post(factories.user(), private=state == "on a draft")
	sentinel = factories.unique()
	return {**factories.comment(author, post, body=f"{WORD} {sentinel}", **{k: v for k, v in overrides.items() if k != "private"}), "sentinel": sentinel}


@pytest.mark.parametrize("state, viewer, listed", _cases(FRONT))
def test_front_page(state, viewer, listed):
	client, post = _arrange(state, viewer, _post_in)

	r = client.get("/")

	_assert_listed(r, client, post, listed)


@pytest.mark.parametrize("state, viewer, listed", _cases(FRONT))
def test_front_page_pins(state, viewer, listed):
	client, post = _arrange(state, viewer, lambda author, state, overrides: _post_in(author, state, {**overrides, "stickied": "someadmin"}))

	r = client.get("/")

	_assert_listed(r, client, post, listed)


@pytest.mark.parametrize("state, viewer, listed", _cases(SEARCH_POSTS))
def test_post_search(state, viewer, listed):
	client, post = _arrange(state, viewer, _post_in)

	r = client.get("/search/posts", params={"q": WORD})

	_assert_listed(r, client, post, listed)


@pytest.mark.parametrize("state, viewer, listed", _cases(COMMENTS))
def test_comment_listing(state, viewer, listed):
	client, comment = _arrange(state, viewer, _comment_in)

	r = client.get("/comments")

	_assert_listed(r, client, comment, listed)


@pytest.mark.parametrize("state, viewer, listed", _cases(SEARCH_COMMENTS))
def test_comment_search(state, viewer, listed):
	client, comment = _arrange(state, viewer, _comment_in)

	r = client.get("/search/comments", params={"q": WORD})

	_assert_listed(r, client, comment, listed)


def _ordinary_cases(table):
	'''The cells of `table` for viewers without admin rights, whose API clients see what their pages do; a hidden comment renders nothing on a page, so only the JSON tells it was left out.'''
	return _cases({cell: listed for cell, listed in table.items() if cell[1] in ("user", "author", "shadowbanned user")})


def _api_client_of(client):
	return as_api(factories.api_token(db.row("users", id=client.user_id)))


@pytest.mark.parametrize("state, viewer, listed", _ordinary_cases(COMMENTS))
def test_comment_listing_json(state, viewer, listed):
	client, comment = _arrange(state, viewer, _comment_in)
	client = _api_client_of(client)

	r = client.get("/comments")

	_assert_listed(r, client, comment, listed)


@pytest.mark.parametrize("state, viewer, listed", _ordinary_cases(SEARCH_COMMENTS))
def test_comment_search_json(state, viewer, listed):
	client, comment = _arrange(state, viewer, _comment_in)
	client = _api_client_of(client)

	r = client.get("/search/comments", params={"q": WORD})

	_assert_listed(r, client, comment, listed)


@pytest.mark.parametrize("path", ["/comments", "/search/comments"])
@pytest.mark.parametrize("viewer", ["sender", "recipient", "admin"])
def test_private_messages_are_never_listed(path, viewer):
	sender, recipient = factories.user(), factories.user()
	sentinel = factories.unique()
	body = f"{WORD} {sentinel}"
	db.insert("comments", author_id=sender["id"], sentto=recipient["id"], created_utc=1, level=1, body=body, body_html=f"<p>{body}</p>", state_mod="VISIBLE", state_report="UNREPORTED", volunteer_janitor_badness=0.5)
	client = as_user({"sender": sender, "recipient": recipient, "admin": factories.admin(3)}[viewer])

	r = client.get(path, params={"q": WORD})

	assert_status(r, 200)
	assert_not_in_payload(r, sentinel)
