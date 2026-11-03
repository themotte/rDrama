'''
Fetching more comments than the post page shows, as HTML fragments:
- GET /viewmore/<post id>/<sort>/<offset>?ids=<comma-separated ids already shown>: the next page of top-level threads.
- GET /morecomments/<comment id>: the replies to a comment too deep in a thread for the post page to show (threads render 9 levels deep).
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


def test_view_more_of_an_unknown_post_is_not_found():
	post = factories.post(factories.user())
	db.delete("votes", submission_id=post["id"])
	db.delete("submissions", id=post["id"])

	assert_status(_viewmore(anon(), post, [1]), 404)


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


def test_more_comments_hides_replies_by_users_you_block():
	post = factories.post(factories.user())
	chain = _thread(post, 10)
	viewer = factories.user()
	db.insert("userblocks", user_id=viewer["id"], target_id=chain[9]["author_id"])

	r = as_user(viewer).get(f"/morecomments/{chain[8]['id']}")

	assert_html(r, 200)
	assert_not_in_payload(r, chain[9]["body"])


def test_more_comments_for_visitors_fetches_replies_at_any_depth():
	post = factories.post(factories.user())
	top = factories.comment(factories.user(), post)
	reply = factories.comment(factories.user(), post, parent=top)

	assert_in_payload(anon().get(f"/morecomments/{top['id']}"), reply["body"])


def test_more_comments_for_users_fetches_only_replies_below_the_shown_depth():
	post = factories.post(factories.user())
	top = factories.comment(factories.user(), post)
	reply = factories.comment(factories.user(), post, parent=top)

	r = as_user(factories.user()).get(f"/morecomments/{top['id']}")

	assert_html(r, 200)
	assert_not_in_payload(r, reply["body"])


def test_more_comments_needs_a_numeric_id():
	assert_status(anon().get("/morecomments/abc"), 400)
