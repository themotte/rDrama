'''
The viewer's saved posts and comments: GET /@<username>/saved/posts and GET /@<username>/saved/comments, for logged-in users, viewed under their own name (in any letter case); another user's name is refused with 403, and an unknown one is 404.

They list what the viewer saved that others can still see (not removed, filtered or deleted), newest first, 25 to a page with "page" (from 1; anything else means 1) choosing the page. Content by users the viewer blocks is left out, except that admins (level 2 and up) still see such posts. Saved comments by shadowbanned authors are left out for viewers who can't see shadowbanned users, and only comments on posts the viewer can see are listed (no private messages, nothing on others' drafts). API clients get {"data": [...]} holding each listed item's JSON object, in order. Anonymous browsers are sent to log in.
'''
import pytest

from files.tests.spec.harness import *

HIDDEN = [
	pytest.param({"state_mod": "REMOVED"}, id="removed"),
	pytest.param({"state_mod": "FILTERED"}, id="filtered"),
	pytest.param({"state_user_deleted_utc": "2020-01-01T00:00:00Z"}, id="deleted"),
]


def _saved(viewer, kind, author=None, **overrides):
	'''An item of `kind` by `author` (a fresh user by default) that `viewer` saved; returns (row, sentinel).'''
	token = factories.unique()
	author = author or factories.user()
	if kind == "posts":
		row = factories.post(author, title=token, **overrides)
		db.insert("save_relationship", user_id=viewer["id"], submission_id=row["id"])
	else:
		row = factories.comment(author, factories.post(factories.user()), body=token, **overrides)
		db.insert("comment_save_relationship", user_id=viewer["id"], comment_id=row["id"])
	return row, token


def _path(viewer, kind):
	return f"/@{viewer['username']}/saved/{kind}"


@pytest.mark.parametrize("kind", ["posts", "comments"])
def test_saved_lists_what_the_viewer_saved(kind):
	viewer = factories.user()
	_, token = _saved(viewer, kind)
	_, others = _saved(factories.user(), kind)

	r = as_user(viewer).get(_path(viewer, kind))

	assert_html(r, 200)
	assert_in_payload(r, token)
	assert_not_in_payload(r, others)


@pytest.mark.parametrize("kind", ["posts", "comments"])
@pytest.mark.parametrize("state", HIDDEN)
def test_saved_leaves_out_hidden_content(kind, state):
	viewer = factories.user()
	_, listed = _saved(viewer, kind)
	_, hidden = _saved(viewer, kind, **state)

	r = as_user(viewer).get(_path(viewer, kind))

	assert_html(r, 200)
	assert_in_payload(r, listed)
	assert_not_in_payload(r, hidden)


@pytest.mark.parametrize("kind", ["posts", "comments"])
def test_saved_leaves_out_content_by_blocked_users(kind):
	viewer, blocked = factories.user(), factories.user()
	db.insert("userblocks", user_id=viewer["id"], target_id=blocked["id"])
	_, listed = _saved(viewer, kind)
	_, token = _saved(viewer, kind, author=blocked)

	r = as_user(viewer).get(_path(viewer, kind))

	assert_html(r, 200)
	assert_in_payload(r, listed)
	assert_not_in_payload(r, token)


@pytest.mark.parametrize("kind", ["posts"])
def test_saved_keeps_content_by_blocked_users_for_admins(kind):
	viewer, blocked = factories.admin(2), factories.user()
	db.insert("userblocks", user_id=viewer["id"], target_id=blocked["id"])
	_, token = _saved(viewer, kind, author=blocked)

	r = as_user(viewer).get(_path(viewer, kind))

	assert_html(r, 200)
	assert_in_payload(r, token)


def test_saved_comments_leave_out_shadowbanned_authors():
	viewer = factories.user()
	_, listed = _saved(viewer, "comments")
	_, token = _saved(viewer, "comments", author=factories.user(shadowbanned="somemod"))

	r = as_user(viewer).get(_path(viewer, "comments"))

	assert_html(r, 200)
	assert_in_payload(r, listed)
	assert_not_in_payload(r, token)


def test_saved_comment_pages_hold_25_listed_comments_though_some_are_hidden():
	viewer = factories.user()
	oldest, *rest = [_saved(viewer, "comments", created_utc=1_700_000_000 + i)[1] for i in range(25)]
	_saved(viewer, "comments", author=factories.user(shadowbanned="somemod"), created_utc=1_700_000_100)

	r = as_user(viewer).get(_path(viewer, "comments"))

	assert_html(r, 200)
	for token in [oldest, *rest]:
		assert_in_payload(r, token)


@pytest.mark.parametrize("kind", ["posts", "comments"])
def test_saved_lists_newest_first(kind):
	viewer = factories.user()
	_, older = _saved(viewer, kind, created_utc=1_700_000_000)
	_, newer = _saved(viewer, kind, created_utc=1_700_000_100)

	r = as_user(viewer).get(_path(viewer, kind))

	assert_html(r, 200)
	assert r.text.index(newer) < r.text.index(older)


@pytest.mark.parametrize("kind", ["posts", "comments"])
@pytest.mark.parametrize("page", [1, 2])
def test_saved_pages_hold_25_items(kind, page):
	viewer = factories.user()
	oldest, *rest = [_saved(viewer, kind, created_utc=1_700_000_000 + i)[1] for i in range(26)]

	r = as_user(viewer).get(_path(viewer, kind), params={"page": page})

	assert_html(r, 200)
	on_page, off_page = (rest, [oldest]) if page == 1 else ([oldest], rest)
	for token in on_page:
		assert_in_payload(r, token)
	for token in off_page:
		assert_not_in_payload(r, token)


@pytest.mark.parametrize("kind", ["posts", "comments"])
@pytest.mark.parametrize("page", ["0", "-2", "x"])
def test_saved_lists_show_the_first_page_for_an_invalid_page(kind, page):
	viewer = factories.user()
	_, token = _saved(viewer, kind)

	r = as_user(viewer).get(_path(viewer, kind), params={"page": page})

	assert_html(r, 200)
	assert_in_payload(r, token)


@pytest.mark.parametrize("kind", ["posts", "comments"])
def test_saved_lists_answer_api_clients_with_json(kind):
	viewer = factories.user()
	older, _ = _saved(viewer, kind, created_utc=1_700_000_000)
	newer, _ = _saved(viewer, kind, created_utc=1_700_000_100)

	r = as_api(factories.api_token(viewer)).get(_path(viewer, kind))

	assert_status(r, 200)
	assert set(r.json) == {"data"}
	assert [item["id"] for item in r.json["data"]] == [newer["id"], older["id"]]


@pytest.mark.parametrize("kind", ["posts", "comments"])
def test_saved_lists_under_another_users_name_are_refused(kind):
	viewer, other = factories.user(), factories.user()
	_saved(other, kind)

	r = as_user(viewer).get(_path(other, kind))

	assert_status(r, 403)


@pytest.mark.parametrize("kind", ["posts", "comments"])
def test_saved_lists_under_an_unknown_name_are_not_found(kind):
	r = as_user(factories.user()).get(_path({"username": factories.unique()}, kind))

	assert_status(r, 404)


@pytest.mark.parametrize("kind", ["posts", "comments"])
def test_saved_lists_find_the_viewer_case_insensitively(kind):
	viewer = factories.user(username=f"Mixed{factories.unique()}")
	_, token = _saved(viewer, kind)

	r = as_user(viewer).get(_path({"username": viewer["username"].upper()}, kind))

	assert_html(r, 200)
	assert_in_payload(r, token)


@pytest.mark.parametrize("kind", ["posts", "comments"])
def test_saved_lists_send_anonymous_browsers_to_log_in(kind):
	path = _path(factories.user(), kind)

	r = anon().get(path)

	assert_login_redirect(r, path)


def _saved_message(viewer):
	message_id = db.execute("SELECT nextval('comments_id_seq')")
	token = factories.unique()
	db.insert("comments", id=message_id, author_id=factories.user()["id"], sentto=viewer["id"], created_utc=1000, parent_submission=None, parent_comment_id=None, level=1, top_comment_id=message_id, body=token, body_html=f"<p>{token}</p>", volunteer_janitor_badness=0.5, state_mod="VISIBLE", state_report="UNREPORTED")
	db.insert("comment_save_relationship", user_id=viewer["id"], comment_id=message_id)
	return token


def test_saved_comments_leave_out_private_messages():
	viewer = factories.user()
	_, listed = _saved(viewer, "comments")
	token = _saved_message(viewer)

	r = as_user(viewer).get(_path(viewer, "comments"))

	assert_html(r, 200)
	assert_in_payload(r, listed)
	assert_not_in_payload(r, token)


@pytest.mark.parametrize("whose", ["others", "own", "admin"])
def test_saved_comments_on_drafts_are_listed_only_to_those_who_see_the_draft(whose):
	viewer = factories.admin(2) if whose == "admin" else factories.user()
	token = factories.unique()
	draft = factories.post(viewer if whose == "own" else factories.user(), private=True)
	comment = factories.comment(factories.user(), draft, body=token)
	db.insert("comment_save_relationship", user_id=viewer["id"], comment_id=comment["id"])

	r = as_user(viewer).get(_path(viewer, "comments"))

	assert_html(r, 200)
	(assert_not_in_payload if whose == "others" else assert_in_payload)(r, token)


def test_saved_comments_json_has_posts_as_the_viewer_may_see_them():
	viewer, op = factories.user(), factories.user()
	db.insert("userblocks", user_id=viewer["id"], target_id=op["id"])
	post = factories.post(op, body=factories.unique())
	comment = factories.comment(factories.user(), post)
	db.insert("comment_save_relationship", user_id=viewer["id"], comment_id=comment["id"])

	r = as_api(factories.api_token(viewer)).get(_path(viewer, "comments"))

	assert_status(r, 200)
	assert [c["id"] for c in r.json["data"]] == [comment["id"]]
	assert_not_in_payload(r, post["body"])
