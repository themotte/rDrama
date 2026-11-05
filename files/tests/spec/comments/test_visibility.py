'''
Which comments a viewer is shown, wherever threads are rendered as pages: the post page (GET /post/<post id>), a comment's own page (GET /comment/<comment id>) and further threads of a post (GET /viewmore/...).

- A comment that moderators removed or filtered, or that its author deleted, is hidden from everyone except its author and moderators (admin level 2 and up). Admins below level 2 don't see it either.
- A comment by a user the viewer blocks is hidden from the viewer, unless it is distinguished as official. (What admins see of users they block is not yet settled.)
- A comment by a user who blocks the viewer is still shown to the viewer.
- Comments marked 18+ are shown like any other.
- A hidden comment doesn't hide its replies: those still shown appear in place. A hidden comment without replies leaves nothing of itself on the page: neither its text nor its author's name.
- Only a comment's author is offered to edit it (POST /edit_comment/<comment id>).
'''
import pytest

from files.tests.spec.harness import *

HIDDEN_STATES = {
	"removed": {"state_mod": "REMOVED", "state_mod_set_by": "somemod"},
	"filtered": {"state_mod": "FILTERED"},
	"deleted": {"state_user_deleted_utc": "2020-01-01T00:00:00Z"},
}

VIEWERS = ["visitor", "user", "author", "admin 1", "admin 2", "admin 3"]

SEES_HIDDEN = {"visitor": False, "user": False, "author": True, "admin 1": False, "admin 2": True, "admin 3": True}


def _client(viewer, author):
	if viewer == "visitor":
		return anon()
	if viewer == "author":
		return as_user(author)
	if viewer == "user":
		return as_user(factories.user())
	return as_user(factories.admin(int(viewer.split()[1])))


def _view(surface, client, post, comment):
	'''Requests the page `surface` that would show `comment`, a top-level comment on `post`.'''
	if surface == "post page":
		return client.get(f"/post/{post['id']}")
	if surface == "permalink":
		return client.get(f"/comment/{comment['id']}")
	shown = factories.comment(factories.user(), post, created_utc=comment["created_utc"] + 1)
	offset = 1
	return client.get(f"/viewmore/{post['id']}/new/{offset}", params={"ids": str(shown["id"])})


SURFACES = ["post page", "permalink", "view more"]


@pytest.mark.parametrize("surface", SURFACES)
@pytest.mark.parametrize("viewer", VIEWERS)
def test_visible_comments_are_shown_to_everyone(viewer, surface):
	author = factories.user()
	post = factories.post(factories.user())
	comment = factories.comment(author, post, created_utc=1000)
	client = _client(viewer, author)

	r = _view(surface, client, post, comment)

	assert_html(r, 200)
	assert_in_payload(r, comment["body"])


@pytest.mark.parametrize("surface", SURFACES)
@pytest.mark.parametrize("viewer", VIEWERS)
@pytest.mark.parametrize("state", HIDDEN_STATES)
def test_removed_filtered_and_deleted_comments_are_shown_only_to_their_author_and_moderators(state, viewer, surface):
	author = factories.user()
	post = factories.post(factories.user())
	comment = factories.comment(author, post, created_utc=1000, **HIDDEN_STATES[state])
	client = _client(viewer, author)

	r = _view(surface, client, post, comment)

	assert_html(r, 200)
	if SEES_HIDDEN[viewer]:
		assert_in_payload(r, comment["body"])
	else:
		assert_not_in_payload(r, comment["body"])


# Blocks (a comment's own page is left out: its meta tags are outside this spec)

@pytest.mark.parametrize("surface", ["post page", "view more"])
def test_comments_by_users_you_block_are_hidden(surface):
	viewer, author = factories.user(), factories.user()
	db.insert("userblocks", user_id=viewer["id"], target_id=author["id"])
	post = factories.post(factories.user())
	comment = factories.comment(author, post, created_utc=1000)

	r = _view(surface, as_user(viewer), post, comment)

	assert_html(r, 200)
	assert_not_in_payload(r, comment["body"])


def test_official_comments_by_users_you_block_are_shown():
	viewer, author = factories.user(), factories.admin(2)
	db.insert("userblocks", user_id=viewer["id"], target_id=author["id"])
	post = factories.post(factories.user())
	comment = factories.comment(author, post, distinguish_level=1)

	r = as_user(viewer).get(f"/post/{post['id']}")

	assert_html(r, 200)
	assert_in_payload(r, comment["body"])


@pytest.mark.parametrize("surface", SURFACES)
def test_comments_by_users_who_block_you_are_shown(surface):
	viewer, author = factories.user(), factories.user()
	db.insert("userblocks", user_id=author["id"], target_id=viewer["id"])
	post = factories.post(factories.user())
	comment = factories.comment(author, post, created_utc=1000)

	r = _view(surface, as_user(viewer), post, comment)

	assert_html(r, 200)
	assert_in_payload(r, comment["body"])


# 18+ comments

@pytest.mark.parametrize("viewer", ["visitor", "user", "18+ user"])
def test_18_plus_comments_are_shown(viewer):
	post = factories.post(factories.user())
	comment = factories.comment(factories.user(), post, over_18=True)
	client = {"visitor": anon, "user": lambda: as_user(factories.user()), "18+ user": lambda: as_user(factories.user(over_18=True))}[viewer]()

	r = client.get(f"/post/{post['id']}")

	assert_html(r, 200)
	assert_in_payload(r, comment["body"])


# Replies of hidden comments

def _hide(state, viewer, comment_author):
	'''Makes comments by `comment_author` hidden from `viewer` in the given way; returns the column values a hidden comment needs.'''
	if state == "blocked":
		db.insert("userblocks", user_id=viewer["id"], target_id=comment_author["id"])
		return {}
	return HIDDEN_STATES[state]


HIDING = [*HIDDEN_STATES, "blocked"]


@pytest.mark.parametrize("state", HIDING)
def test_replies_of_a_hidden_comment_are_shown(state):
	viewer, author = factories.user(), factories.user()
	post = factories.post(factories.user())
	hidden = factories.comment(author, post, **_hide(state, viewer, author))
	reply = factories.comment(factories.user(), post, parent=hidden)

	r = as_user(viewer).get(f"/post/{post['id']}")

	assert_html(r, 200)
	assert_in_payload(r, reply["body"])
	assert_not_in_payload(r, hidden["body"])


@pytest.mark.parametrize("state", HIDDEN_STATES)
def test_replies_of_a_hidden_comment_are_shown_on_its_own_page(state):
	post = factories.post(factories.user())
	hidden = factories.comment(factories.user(), post, **HIDDEN_STATES[state])
	reply = factories.comment(factories.user(), post, parent=hidden)

	r = anon().get(f"/comment/{hidden['id']}")

	assert_html(r, 200)
	assert_in_payload(r, reply["body"])
	assert_not_in_payload(r, hidden["body"])


@pytest.mark.parametrize("state", HIDING)
def test_a_hidden_comment_without_replies_leaves_nothing_of_itself(state):
	viewer, author = factories.user(), factories.user(username=factories.unique("author"))
	post = factories.post(factories.user())
	hidden = factories.comment(author, post, **_hide(state, viewer, author))
	shown = factories.comment(factories.user(), post)

	r = as_user(viewer).get(f"/post/{post['id']}")

	assert_html(r, 200)
	assert_in_payload(r, shown["body"])
	assert_not_in_payload(r, hidden["body"])
	assert_not_in_payload(r, author["username"])


# Affordances

@pytest.mark.parametrize("viewer", ["author", "user", "visitor"])
def test_only_the_author_is_offered_to_edit_a_comment(viewer):
	author = factories.user()
	post = factories.post(factories.user())
	comment = factories.comment(author, post)
	client = {"author": lambda: as_user(author), "user": lambda: as_user(factories.user()), "visitor": anon}[viewer]()

	r = client.get(f"/post/{post['id']}")

	assert_html(r, 200)
	if viewer == "author":
		assert_in_payload(r, f"/edit_comment/{comment['id']}")
	else:
		assert_not_in_payload(r, f"/edit_comment/{comment['id']}")
