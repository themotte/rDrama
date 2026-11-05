'''
Voter lists, for admins of level 3 (anonymous browsers are sent to log in; lower levels and API clients are refused with 403):
- GET /@<username>/upvoters and /@<username>/downvoters rank the users who voted up (down) on the user's posts and comments, by how many such votes each cast.
- GET /@<username>/upvoting and /@<username>/downvoting rank the authors whose posts and comments the user voted up (down), by how many such votes the user cast on each.

Only votes on content others can see count: not on removed, filtered, deleted or anonymous ("ghost") posts and comments, nor on drafts. A user's votes on their own content count like anyone's. The 25 highest-ranked users are listed (tied users oldest account, lowest id, first), each linking to the drilldown of their votes (/@<username>/<list>/<user id>/posts). The viewing admin's own row is added after the list when they aren't in it.

Each drilldown, GET /@<username>/<list>/<user id>/posts and /@<username>/<list>/<user id>/comments, lists the posts (comments) behind one row: for upvoters and downvoters, the user's content that the other user voted on that way; for upvoting and downvoting, the other user's content the user voted on that way. Only content others can see is listed, newest first, 25 to a page, with "page" (from 1; anything else means 1) choosing the page. A user id that isn't a valid id is 404.
'''
import pytest

from files.tests.spec.harness import *

# list name -> (vote type, whether the list ranks voters on the user's content rather than authors of what the user voted on)
LISTS = {
	"upvoters": (1, True),
	"downvoters": (-1, True),
	"upvoting": (1, False),
	"downvoting": (-1, False),
}

HIDDEN = [
	pytest.param({"state_mod": "REMOVED"}, id="removed"),
	pytest.param({"state_mod": "FILTERED"}, id="filtered"),
	pytest.param({"state_user_deleted_utc": "2020-01-01T00:00:00Z"}, id="deleted"),
	pytest.param({"ghost": True}, id="ghost"),
]


def _profile_user():
	'''A user whose own self-votes (which posting leaves) are taken back, so they don't rank on their own lists.'''
	return factories.user()


def _item(author, what, **overrides):
	'''A post or comment by `author` in the given state, with the author's self-vote taken back; returns (row, sentinel).'''
	token = factories.unique()
	if what == "posts":
		row = factories.post(author, title=token, **overrides)
		db.delete("votes", user_id=author["id"], submission_id=row["id"])
	else:
		row = factories.comment(author, factories.post(factories.user()), body=token, **overrides)
		db.delete("commentvotes", user_id=author["id"], comment_id=row["id"])
	return row, token


def _vote(voter, what, row, vote_type):
	if what == "posts":
		db.insert("votes", user_id=voter["id"], submission_id=row["id"], vote_type=vote_type)
	else:
		db.insert("commentvotes", user_id=voter["id"], comment_id=row["id"], vote_type=vote_type)


def _cast(name, user, other, what, vote_type=None, **overrides):
	'''One vote between `user` (whose list it is) and `other`, as `name` counts it: `other` voting on `user`'s item, or `user` voting on `other`'s. Returns the item's sentinel.'''
	list_vote, on_users_content = LISTS[name]
	author, voter = (user, other) if on_users_content else (other, user)
	row, token = _item(author, what, **overrides)
	_vote(voter, what, row, list_vote if vote_type is None else vote_type)
	return token


def _drilldown(name, user, other, what):
	return f"/@{user['username']}/{name}/{other['id']}/{what}"


def _row_link(name, user, other):
	return f"/@{user['username']}/{name}/{other['id']}/posts"


# Who may look

LIST_ROUTES = [f"/@{{username}}/{name}" for name in LISTS] + [f"/@{{username}}/{name}/{{other_id}}/{what}" for name in LISTS for what in ("posts", "comments")]


@pytest.mark.parametrize("route", LIST_ROUTES)
def test_voter_lists_send_anonymous_browsers_to_log_in(route):
	path = route.format(username=factories.user()["username"], other_id=factories.user()["id"])

	r = anon().get(path)

	assert_login_redirect(r, path)


@pytest.mark.parametrize("route", LIST_ROUTES)
def test_voter_lists_refuse_admins_below_level_3(route):
	path = route.format(username=factories.user()["username"], other_id=factories.user()["id"])

	r = as_user(factories.admin(2)).get(path)

	assert_status(r, 403)


@pytest.mark.parametrize("route", LIST_ROUTES)
def test_voter_lists_refuse_api_clients(route):
	path = route.format(username=factories.user()["username"], other_id=factories.user()["id"])

	r = as_api(factories.api_token(factories.admin(3))).get(path)

	assert_status(r, 403)


@pytest.mark.parametrize("name", LISTS)
def test_voter_list_of_an_unknown_user_is_not_found(name):
	r = as_user(factories.admin(3)).get(f"/@{factories.unique()}/{name}")

	assert_status(r, 404)


# The ranked lists

@pytest.mark.parametrize("name", LISTS)
@pytest.mark.parametrize("what", ["posts", "comments"])
def test_voter_list_counts_votes_on_visible_content(name, what):
	user, other = _profile_user(), factories.user()
	_cast(name, user, other, what)

	r = as_user(factories.admin(3)).get(f"/@{user['username']}/{name}")

	assert_html(r, 200)
	assert_in_payload(r, other["username"])
	assert_in_payload(r, _row_link(name, user, other))


@pytest.mark.parametrize("name", LISTS)
@pytest.mark.parametrize("what", ["posts", "comments"])
@pytest.mark.parametrize("state", HIDDEN)
def test_voter_list_ignores_votes_on_hidden_content(name, what, state):
	user, other = _profile_user(), factories.user()
	_cast(name, user, other, what, **state)

	r = as_user(factories.admin(3)).get(f"/@{user['username']}/{name}")

	assert_html(r, 200)
	assert_not_in_payload(r, other["username"])


@pytest.mark.parametrize("name", LISTS)
def test_voter_list_ignores_votes_the_other_way(name):
	user, other = _profile_user(), factories.user()
	_cast(name, user, other, "posts", vote_type=-LISTS[name][0])

	r = as_user(factories.admin(3)).get(f"/@{user['username']}/{name}")

	assert_html(r, 200)
	assert_not_in_payload(r, other["username"])


@pytest.mark.parametrize("name", LISTS)
def test_voter_list_ignores_other_users_votes(name):
	user, other = _profile_user(), factories.user()
	_cast(name, factories.user(), other, "posts")

	r = as_user(factories.admin(3)).get(f"/@{user['username']}/{name}")

	assert_html(r, 200)
	assert_not_in_payload(r, other["username"])


@pytest.mark.parametrize("name", LISTS)
def test_voter_list_ranks_by_votes_across_posts_and_comments(name):
	user = _profile_user()
	three, two, one = factories.user(), factories.user(), factories.user()
	_cast(name, user, three, "posts")
	_cast(name, user, three, "comments")
	_cast(name, user, three, "comments")
	_cast(name, user, two, "posts")
	_cast(name, user, two, "posts")
	_cast(name, user, one, "comments")

	r = as_user(factories.admin(3)).get(f"/@{user['username']}/{name}")

	assert_html(r, 200)
	assert r.text.index(three["username"]) < r.text.index(two["username"]) < r.text.index(one["username"])


@pytest.mark.parametrize("name", LISTS)
def test_voter_list_breaks_ties_by_account_age(name):
	user = _profile_user()
	tied = [factories.user() for _ in range(4)]
	for other in reversed(tied):
		_cast(name, user, other, "posts")
	for other in reversed(tied):
		db.update("users", {"id": other["id"]}, bio=factories.unique())

	r = as_user(factories.admin(3)).get(f"/@{user['username']}/{name}")

	assert_html(r, 200)
	positions = [r.text.index(other["username"]) for other in tied]
	assert positions == sorted(positions)


@pytest.mark.parametrize("name", LISTS)
def test_voter_list_counts_the_users_own_votes(name):
	user = _profile_user()
	_cast(name, user, user, "posts")

	r = as_user(factories.admin(3)).get(f"/@{user['username']}/{name}")

	assert_html(r, 200)
	assert_in_payload(r, _row_link(name, user, user))


@pytest.mark.parametrize("name", LISTS)
def test_voter_list_shows_the_top_25(name):
	user = _profile_user()
	others = [factories.user() for _ in range(26)]
	for other in others[:25]:
		_cast(name, user, other, "comments")
		_cast(name, user, other, "comments")
	_cast(name, user, others[25], "comments")

	r = as_user(factories.admin(3)).get(f"/@{user['username']}/{name}")

	assert_html(r, 200)
	for other in others[:25]:
		assert_in_payload(r, other["username"])
	assert_not_in_payload(r, others[25]["username"])


@pytest.mark.parametrize("name", LISTS)
def test_voter_list_adds_the_viewers_row_when_they_are_not_listed(name):
	user, viewer = _profile_user(), factories.admin(3)
	_cast(name, user, factories.user(), "posts")

	r = as_user(viewer).get(f"/@{user['username']}/{name}")

	assert_html(r, 200)
	assert r.text.count(_row_link(name, user, viewer)) == 1


@pytest.mark.parametrize("name", LISTS)
def test_voter_list_shows_a_listed_viewer_once(name):
	user, viewer = _profile_user(), factories.admin(3)
	_cast(name, user, viewer, "posts")

	r = as_user(viewer).get(f"/@{user['username']}/{name}")

	assert_html(r, 200)
	assert r.text.count(_row_link(name, user, viewer)) == 1


@pytest.mark.parametrize("name", LISTS)
def test_voter_list_adds_the_viewers_row_when_they_rank_below_the_top_25(name):
	user, viewer = _profile_user(), factories.admin(3)
	for _ in range(25):
		other = factories.user()
		_cast(name, user, other, "comments")
		_cast(name, user, other, "comments")
	_cast(name, user, viewer, "comments")

	r = as_user(viewer).get(f"/@{user['username']}/{name}")

	assert_html(r, 200)
	assert r.text.count(_row_link(name, user, viewer)) == 1


# Drilldowns

@pytest.mark.parametrize("name", LISTS)
@pytest.mark.parametrize("what", ["posts", "comments"])
def test_drilldown_lists_the_voted_content(name, what):
	user, other = _profile_user(), factories.user()
	token = _cast(name, user, other, what)

	r = as_user(factories.admin(3)).get(_drilldown(name, user, other, what))

	assert_html(r, 200)
	assert_in_payload(r, token)


@pytest.mark.parametrize("name", LISTS)
@pytest.mark.parametrize("what", ["posts", "comments"])
@pytest.mark.parametrize("state", HIDDEN)
def test_drilldown_omits_hidden_content(name, what, state):
	user, other = _profile_user(), factories.user()
	listed = _cast(name, user, other, what)
	token = _cast(name, user, other, what, **state)

	r = as_user(factories.admin(3)).get(_drilldown(name, user, other, what))

	assert_html(r, 200)
	assert_in_payload(r, listed)
	assert_not_in_payload(r, token)


@pytest.mark.parametrize("name", LISTS)
@pytest.mark.parametrize("what", ["posts", "comments"])
def test_drilldown_omits_votes_the_other_way(name, what):
	user, other = _profile_user(), factories.user()
	listed = _cast(name, user, other, what)
	token = _cast(name, user, other, what, vote_type=-LISTS[name][0])

	r = as_user(factories.admin(3)).get(_drilldown(name, user, other, what))

	assert_html(r, 200)
	assert_in_payload(r, listed)
	assert_not_in_payload(r, token)


@pytest.mark.parametrize("name", LISTS)
@pytest.mark.parametrize("what", ["posts", "comments"])
def test_drilldown_omits_other_pairs(name, what):
	user, other = _profile_user(), factories.user()
	listed = _cast(name, user, other, what)
	elsewhere = [_cast(name, user, factories.user(), what), _cast(name, factories.user(), other, what)]

	r = as_user(factories.admin(3)).get(_drilldown(name, user, other, what))

	assert_html(r, 200)
	assert_in_payload(r, listed)
	for token in elsewhere:
		assert_not_in_payload(r, token)


@pytest.mark.parametrize("name", LISTS)
@pytest.mark.parametrize("what", ["posts", "comments"])
def test_drilldown_lists_newest_first(name, what):
	user, other = _profile_user(), factories.user()
	older = _cast(name, user, other, what, created_utc=1_700_000_000)
	newer = _cast(name, user, other, what, created_utc=1_700_000_100)

	r = as_user(factories.admin(3)).get(_drilldown(name, user, other, what))

	assert_html(r, 200)
	assert r.text.index(newer) < r.text.index(older)


@pytest.mark.parametrize("name", LISTS)
@pytest.mark.parametrize("what", ["posts", "comments"])
@pytest.mark.parametrize("page", [1, 2])
def test_drilldown_pages_hold_25_items(name, what, page):
	user, other = _profile_user(), factories.user()
	oldest, *rest = [_cast(name, user, other, what, created_utc=1_700_000_000 + i) for i in range(26)]

	r = as_user(factories.admin(3)).get(_drilldown(name, user, other, what), params={"page": page})

	assert_html(r, 200)
	on_page, off_page = (rest, [oldest]) if page == 1 else ([oldest], rest)
	for token in on_page:
		assert_in_payload(r, token)
	for token in off_page:
		assert_not_in_payload(r, token)


@pytest.mark.parametrize("name", LISTS)
def test_drilldown_of_an_unknown_user_is_not_found(name):
	r = as_user(factories.admin(3)).get(f"/@{factories.unique()}/{name}/{factories.user()['id']}/posts")

	assert_status(r, 404)


@pytest.mark.parametrize("name", LISTS)
@pytest.mark.parametrize("uid", ["x", "0", "99999999999"])
def test_drilldown_of_an_invalid_user_id_is_not_found(name, uid):
	r = as_user(factories.admin(3)).get(f"/@{factories.user()['username']}/{name}/{uid}/posts")

	assert_status(r, 404)


@pytest.mark.parametrize("name", LISTS)
@pytest.mark.parametrize("page", ["0", "-2", "x"])
def test_drilldown_shows_the_first_page_for_an_invalid_page(name, page):
	user, other = _profile_user(), factories.user()
	token = _cast(name, user, other, "posts")

	r = as_user(factories.admin(3)).get(_drilldown(name, user, other, "posts"), params={"page": page})

	assert_html(r, 200)
	assert_in_payload(r, token)


@pytest.mark.parametrize("name", LISTS)
@pytest.mark.parametrize("what", ["posts", "comments"])
def test_drilldown_of_a_private_profile_is_shown(name, what):
	user, other = _profile_user(), factories.user()
	db.update("users", {"id": user["id"]}, is_private=True)
	token = _cast(name, user, other, what)

	r = as_user(factories.admin(3)).get(_drilldown(name, user, other, what))

	assert_html(r, 200)
	assert_in_payload(r, token)


@pytest.mark.parametrize("name", LISTS)
def test_voter_list_ignores_votes_on_drafts(name):
	user, other = _profile_user(), factories.user()
	_cast(name, user, other, "posts", private=True)

	r = as_user(factories.admin(3)).get(f"/@{user['username']}/{name}")

	assert_html(r, 200)
	assert_not_in_payload(r, other["username"])


@pytest.mark.parametrize("name", LISTS)
def test_drilldown_omits_drafts(name):
	user, other = _profile_user(), factories.user()
	listed = _cast(name, user, other, "posts")
	draft = _cast(name, user, other, "posts", private=True)

	r = as_user(factories.admin(3)).get(_drilldown(name, user, other, "posts"))

	assert_html(r, 200)
	assert_in_payload(r, listed)
	assert_not_in_payload(r, draft)
