'''
Fetching more comments than the post page shows, as HTML fragments:
- GET /viewmore/<post id>/<sort>/<offset>?ids=<comma-separated ids already shown>: the next page of top-level threads.
- GET /morecomments/<comment id>: the replies to a comment too deep in a thread for the post page to show (threads render 9 levels deep), shown by the post page's rules (hidden comments as placeholders for replies the viewer may see), ordered by its "sort" parameter as the post page orders comments (without a known one, in the viewer's default comment order: newest first for visitors), nine levels deep.

On an 18+ post both are refused with 403 to visitors who haven't confirmed their age and to users who aren't 18+, as the post page itself asks them to confirm first.
'''
import pytest

from files.tests.spec.harness import *


def _viewmore(client, post, ids, sort="new", offset=1):
	return client.get(f"/viewmore/{post['id']}/{sort}/{offset}", params={"ids": ",".join(str(i) for i in ids)})


def test_view_more_fetches_threads_not_yet_shown():
	post = factories.post(factories.user())
	shown = factories.comment(factories.user(), post, created_utc=2000)
	reply = factories.comment(factories.user(), post, parent=shown)
	unseen = factories.comment(factories.user(), post, created_utc=1000)
	unseen_reply = factories.comment(factories.user(), post, parent=unseen)

	r = _viewmore(anon(), post, [shown["id"], reply["id"]])

	assert_html(r, 200)
	assert_in_payload(r, unseen["body"])
	assert_in_payload(r, unseen_reply["body"])
	assert_not_in_payload(r, shown["body"])


def test_view_more_pages_through_threads_200_comments_at_a_time():
	post = factories.post(factories.user())
	shown = factories.comment(factories.user(), post, created_utc=3000)
	big = factories.comment(factories.user(), post, created_utc=2000)
	for _ in range(199):
		factories.comment(factories.user(), post, parent=big)
	last = factories.comment(factories.user(), post, created_utc=1000)

	first = _viewmore(anon(), post, [shown["id"]])
	assert_in_payload(first, big["body"])
	assert_not_in_payload(first, last["body"])

	second = _viewmore(anon(), post, [shown["id"], big["id"]], offset=2)
	assert_in_payload(second, last["body"])


def test_view_more_by_newest_skips_comments_newer_than_those_shown():
	'''With the "new" sort, threads started after the page was loaded are left out.'''
	post = factories.post(factories.user())
	shown = factories.comment(factories.user(), post, created_utc=2000)
	newer = factories.comment(factories.user(), post, created_utc=3000)
	older = factories.comment(factories.user(), post, created_utc=1000)

	r = _viewmore(anon(), post, [shown["id"]], sort="new")

	assert_in_payload(r, older["body"])
	assert_not_in_payload(r, newer["body"])


def test_view_more_by_other_sorts_includes_newer_comments():
	post = factories.post(factories.user())
	shown = factories.comment(factories.user(), post, created_utc=2000)
	newer = factories.comment(factories.user(), post, created_utc=3000)

	assert_in_payload(_viewmore(anon(), post, [shown["id"]], sort="old"), newer["body"])


def test_view_more_with_an_unknown_sort_uses_the_viewers_default():
	post = factories.post(factories.user())
	shown = factories.comment(factories.user(), post, created_utc=3000)
	older = factories.comment(factories.user(), post, created_utc=1000)
	newer = factories.comment(factories.user(), post, created_utc=2000)
	u = factories.user(defaultsortingcomments="old")

	r = _viewmore(as_user(u), post, [shown["id"]], sort="bogus")

	assert r.text.index(older["body"]) < r.text.index(newer["body"])


def test_view_more_leaves_out_pinned_comments():
	'''Pinned comments are always on the first page.'''
	post = factories.post(factories.user())
	shown = factories.comment(factories.user(), post, created_utc=2000)
	pinned = factories.comment(factories.user(), post, created_utc=1000, is_pinned="somemod")

	r = _viewmore(anon(), post, [shown["id"]], sort="old")

	assert_html(r, 200)
	assert_not_in_payload(r, pinned["body"])


@pytest.mark.parametrize("ids", [None, "", "1,x"])
def test_view_more_needs_the_shown_ids(ids):
	post = factories.post(factories.user())

	r = anon().get(f"/viewmore/{post['id']}/new/{1}", params=None if ids is None else {"ids": ids})

	assert_status(r, 400)


def test_view_more_needs_a_numeric_offset():
	post = factories.post(factories.user())

	assert_status(anon().get(f"/viewmore/{post['id']}/new/x", params={"ids": "1"}), 400)


def test_view_more_of_an_unknown_post_is_not_found():
	post = factories.post(factories.user())
	db.delete("votes", submission_id=post["id"])
	db.delete("submissions", id=post["id"])

	assert_status(_viewmore(anon(), post, [1]), 404)


def test_view_more_of_someone_elses_draft_is_not_found():
	draft = factories.post(factories.user(), private=True)
	shown = factories.comment(factories.user(), draft)

	assert_status(_viewmore(as_user(factories.user()), draft, [shown["id"]]), 404)


def test_more_comments_of_someone_elses_draft_is_not_found():
	draft = factories.post(factories.user(), private=True)
	top = factories.comment(factories.user(), draft)
	factories.comment(factories.user(), draft, parent=top)

	assert_status(anon().get(f"/morecomments/{top['id']}"), 404)


# Deep threads

def _thread(post, depth):
	chain = [factories.comment(factories.user(), post)]
	for _ in range(depth - 1):
		chain.append(factories.comment(factories.user(), post, parent=chain[-1]))
	return chain


def test_post_page_shows_threads_nine_levels_deep():
	post = factories.post(factories.user())
	chain = _thread(post, 10)

	r = anon().get(f"/post/{post['id']}")

	assert_in_payload(r, chain[8]["body"])
	assert_not_in_payload(r, chain[9]["body"])


@pytest.mark.parametrize("viewer", ["visitor", "user"])
def test_more_comments_fetches_the_rest_of_a_deep_thread(viewer):
	post = factories.post(factories.user())
	chain = _thread(post, 11)

	r = (anon() if viewer == "visitor" else as_user(factories.user())).get(f"/morecomments/{chain[8]['id']}")

	assert_html(r, 200)
	assert_in_payload(r, chain[9]["body"])
	assert_in_payload(r, chain[10]["body"])
	assert_not_in_payload(r, chain[8]["body"])


@pytest.mark.parametrize("sort, default, first", [("old", "new", "older"), ("new", "old", "newer"), (None, "new", "newer"), ("bogus", "new", "newer")])
def test_more_comments_orders_replies_by_the_sort_asked_for(sort, default, first):
	'''Without a known sort, the replies come in the viewer's default order.'''
	post = factories.post(factories.user())
	top = factories.comment(factories.user(), post)
	older = factories.comment(factories.user(), post, parent=top, created_utc=1000)
	newer = factories.comment(factories.user(), post, parent=top, created_utc=2000)

	r = as_user(factories.user(defaultsortingcomments=default)).get(f"/morecomments/{top['id']}", params={"sort": sort} if sort else {})

	assert_html(r, 200)
	expected = [older, newer] if first == "older" else [newer, older]
	assert_in_order(r, [c["body"] for c in expected])


@pytest.mark.parametrize("sort, shown", [("old", "old"), (None, "new")])
def test_a_deep_threads_link_to_its_rest_keeps_the_pages_sort(sort, shown):
	'''Small screens get a link to the comment's own page instead of fetching the rest in place; it carries the sort the page shows (for visitors without one, new).'''
	post = factories.post(factories.user())
	chain = _thread(post, 10)

	r = anon().get(f"/post/{post['id']}", params={"sort": sort} if sort else {})

	assert_html(r, 200)
	assert_in_payload(r, f"/{chain[8]['id']}?sort={shown}#context")


def test_more_comments_hides_replies_by_users_you_block():
	post = factories.post(factories.user())
	chain = _thread(post, 10)
	viewer = factories.user()
	db.insert("userblocks", user_id=viewer["id"], target_id=chain[9]["author_id"])

	r = as_user(viewer).get(f"/morecomments/{chain[8]['id']}")

	assert_html(r, 200)
	assert_not_in_payload(r, chain[9]["body"])


@pytest.mark.parametrize("viewer", ["visitor", "user"])
def test_more_comments_fetches_the_replies_of_a_comment_at_any_depth(viewer):
	post = factories.post(factories.user())
	top = factories.comment(factories.user(), post)
	reply = factories.comment(factories.user(), post, parent=top)
	elsewhere = factories.comment(factories.user(), post, parent=factories.comment(factories.user(), post))

	r = (anon() if viewer == "visitor" else as_user(factories.user())).get(f"/morecomments/{top['id']}")

	assert_html(r, 200)
	assert_in_payload(r, reply["body"])
	assert_not_in_payload(r, elsewhere["body"])
	assert_not_in_payload(r, top["body"])


@pytest.mark.parametrize("viewer", ["visitor", "user"])
def test_more_comments_shows_replies_under_a_hidden_reply(viewer):
	post = factories.post(factories.user())
	top = factories.comment(factories.user(), post)
	removed = factories.comment(factories.user(), post, parent=top, state_mod="REMOVED", state_mod_set_by="somemod")
	below = factories.comment(factories.user(), post, parent=removed)

	r = (anon() if viewer == "visitor" else as_user(factories.user())).get(f"/morecomments/{top['id']}")

	assert_html(r, 200)
	assert_in_payload(r, below["body"])
	assert_not_in_payload(r, removed["body"])


def test_more_comments_shows_moderators_hidden_replies_at_any_depth():
	post = factories.post(factories.user())
	top = factories.comment(factories.user(), post)
	reply = factories.comment(factories.user(), post, parent=top)
	removed = factories.comment(factories.user(), post, parent=reply, state_mod="REMOVED", state_mod_set_by="somemod")

	r = as_user(factories.admin(2)).get(f"/morecomments/{top['id']}")

	assert_html(r, 200)
	assert_in_payload(r, removed["body"])


@pytest.mark.parametrize("order", ["old", "new"])
def test_more_comments_follows_the_viewers_comment_order(order):
	post = factories.post(factories.user())
	top = factories.comment(factories.user(), post)
	newer = factories.comment(factories.user(), post, parent=top, created_utc=2000)
	older = factories.comment(factories.user(), post, parent=top, created_utc=1000)

	r = as_user(factories.user(defaultsortingcomments=order)).get(f"/morecomments/{top['id']}")

	assert_html(r, 200)
	first, second = (older, newer) if order == "old" else (newer, older)
	assert r.text.index(first["body"]) < r.text.index(second["body"])


def test_more_comments_needs_a_numeric_id():
	assert_status(anon().get("/morecomments/abc"), 400)


def _message(author, recipient, parent=None):
	'''A private message, or a reply within a private conversation.'''
	return factories.message(author, recipient, parent, created_utc=1000)


@pytest.mark.parametrize("viewer", ["visitor", "user"])
@pytest.mark.parametrize("depth", [0, 8], ids=["first message", "deep in the conversation"])
def test_more_comments_does_not_reveal_private_messages(viewer, depth):
	sender, recipient = factories.user(), factories.user()
	chain = [_message(sender, recipient)]
	for i in range(11):
		chain.append(_message(recipient if i % 2 == 0 else sender, sender if i % 2 == 0 else recipient, parent=chain[-1]))
	client = anon() if viewer == "visitor" else as_user(factories.user())

	assert_status(client.get(f"/morecomments/{chain[depth]['id']}"), 404)


def test_more_comments_of_an_unknown_comment_is_not_found():
	comment = factories.comment(factories.user(), factories.post(factories.user()))
	db.delete("commentvotes", comment_id=comment["id"])
	db.delete("comments", id=comment["id"])

	assert_status(anon().get(f"/morecomments/{comment['id']}"), 404)


def _fetch_more(which, client, post):
	if which == "view more":
		shown = factories.comment(factories.user(), post, created_utc=2000)
		factories.comment(factories.user(), post, body=factories.unique(), created_utc=1000)
		return _viewmore(client, post, [shown["id"]])
	chain = _thread(post, 11)
	return client.get(f"/morecomments/{chain[8]['id']}")


@pytest.mark.parametrize("which", ["view more", "more comments"])
@pytest.mark.parametrize("viewer", ["visitor", "user"])
def test_fetching_more_of_an_18_plus_post_needs_age_confirmation(which, viewer):
	post = factories.post(factories.user(), over_18=True)
	client = anon() if viewer == "visitor" else as_user(factories.user())

	r = _fetch_more(which, client, post)

	assert_status(r, 403)


@pytest.mark.parametrize("which", ["view more", "more comments"])
@pytest.mark.parametrize("viewer", ["confirmed visitor", "18+ user"])
def test_fetching_more_of_an_18_plus_post_after_age_confirmation(which, viewer):
	post = factories.post(factories.user(), over_18=True)
	if viewer == "confirmed visitor":
		client = anon()
		assert_redirect(client.post("/allow_nsfw", {"redir": f"/post/{post['id']}"}), f"/post/{post['id']}")
	else:
		client = as_user(factories.user(over_18=True))

	r = _fetch_more(which, client, post)

	assert_html(r, 200)


@pytest.mark.parametrize("viewer", ["author", "user"])
def test_more_comments_shows_shadowbanned_replies_only_to_their_author(viewer):
	author = factories.user(shadowbanned="somemod")
	post = factories.post(factories.user())
	top = factories.comment(factories.user(), post)
	reply = factories.comment(author, post, parent=top, body=factories.unique())

	r = as_user(author if viewer == "author" else factories.user()).get(f"/morecomments/{top['id']}")

	assert_html(r, 200)
	(assert_in_payload if viewer == "author" else assert_not_in_payload)(r, reply["body"])
