'''
GET /leaderboard, for admins of level 2 (anonymous browsers are sent to log in; lower levels and API clients are refused with 403).

The page shows several boards, each a section whose element id is "leaderboard-<board>":
- "truescore", "followers", "posts", "comments": the 25 users with the highest truescore, follower count, post count and comment count, highest first.
- "blocked": the 25 users blocked by the most users, most blocked first; users nobody blocks aren't ranked.
- "received-downvotes" and "given-upvotes": the 25 users who received the most downvotes, and who gave the most upvotes, on posts and comments. These are expensive to compute, so the `leaderboard_recalc` command computes them ahead of time; until it has run, the page leaves both out.

The viewing admin's own row is added after a board's list when they aren't in it (on the blocked board, also when nobody blocks them).
'''
import pytest

from files.tests.spec.harness import *

# board -> users column it ranks by
SIMPLE_BOARDS = {
	"truescore": "truescore",
	"followers": "stored_subscriber_count",
	"posts": "post_count",
	"comments": "comment_count",
}

HIGH = 1_000_000
'''A value no seed user's counters come near, so fixture users rank first.'''


def _board(r, board) -> str:
	'''The part of the page holding one board's table.'''
	start = r.text.index(f'id="leaderboard-{board}"')
	return r.text[start:r.text.index("</table>", start)]


def _rows_of(section, user) -> int:
	'''How many times `user` is mentioned in a board, relative to how many mentions one row makes: compared against a user known to hold exactly one row.'''
	return section.count(user["username"])


def _has_board(r, board) -> bool:
	return f'id="leaderboard-{board}"' in r.text


def _ranked(column, value):
	return factories.user(**{column: value})


# Who may look

def test_leaderboard_sends_anonymous_browsers_to_log_in():
	r = anon().get("/leaderboard")

	assert_login_redirect(r, "/leaderboard")


def test_leaderboard_refuses_admins_below_level_2():
	r = as_user(factories.admin(1)).get("/leaderboard")

	assert_status(r, 403)


def test_leaderboard_refuses_api_clients():
	r = as_api(factories.api_token(factories.admin(2))).get("/leaderboard")

	assert_status(r, 403)


def test_leaderboard_shows_to_level_2_admins():
	r = as_user(factories.admin(2)).get("/leaderboard")

	assert_html(r, 200)
	for board in [*SIMPLE_BOARDS, "blocked"]:
		assert _has_board(r, board), board


# The boards of user counters

@pytest.mark.parametrize("board, column", SIMPLE_BOARDS.items())
def test_simple_board_ranks_highest_first(board, column):
	low, high, middle = _ranked(column, HIGH + 1), _ranked(column, HIGH + 3), _ranked(column, HIGH + 2)

	r = as_user(factories.admin(2)).get("/leaderboard")

	assert_html(r, 200)
	section = _board(r, board)
	assert section.index(high["username"]) < section.index(middle["username"]) < section.index(low["username"])


@pytest.mark.parametrize("board, column", SIMPLE_BOARDS.items())
def test_simple_board_ranks_by_its_own_counter(board, column):
	others = [c for c in SIMPLE_BOARDS.values() if c != column]
	ranked = _ranked(column, HIGH + 1)
	high_elsewhere = factories.user(**{c: HIGH + 1 for c in others})
	for _ in range(25):
		_ranked(column, HIGH)

	r = as_user(factories.admin(2)).get("/leaderboard")

	assert_html(r, 200)
	section = _board(r, board)
	assert ranked["username"] in section
	assert high_elsewhere["username"] not in section


@pytest.mark.parametrize("board, column", SIMPLE_BOARDS.items())
def test_simple_board_lists_25_users(board, column):
	users = [_ranked(column, HIGH + 26 - i) for i in range(26)]

	r = as_user(factories.admin(2)).get("/leaderboard")

	assert_html(r, 200)
	section = _board(r, board)
	for u in users[:25]:
		assert u["username"] in section, u["username"]
	assert users[25]["username"] not in section


@pytest.mark.parametrize("board, column", SIMPLE_BOARDS.items())
def test_simple_board_adds_the_viewers_row_when_they_rank_below_the_top_25(board, column):
	listed = [_ranked(column, HIGH + i) for i in range(25)]
	viewer = factories.admin(2)

	r = as_user(viewer).get("/leaderboard")

	assert_html(r, 200)
	section = _board(r, board)
	assert _rows_of(section, viewer) == _rows_of(section, listed[0]) > 0


@pytest.mark.parametrize("board, column", SIMPLE_BOARDS.items())
def test_simple_board_shows_a_listed_viewer_once(board, column):
	viewer = factories.admin(2, **{column: HIGH + 1})
	peer = _ranked(column, HIGH)

	r = as_user(viewer).get("/leaderboard")

	assert_html(r, 200)
	section = _board(r, board)
	assert _rows_of(section, viewer) == _rows_of(section, peer) > 0


# The blocked board

def _block(blocker, target):
	db.insert("userblocks", user_id=blocker["id"], target_id=target["id"])


def test_blocked_board_ranks_the_most_blocked_first():
	once, thrice, twice = factories.user(), factories.user(), factories.user()
	for target, blockers in ((once, 1), (thrice, 3), (twice, 2)):
		for _ in range(blockers):
			_block(factories.user(), target)

	r = as_user(factories.admin(2)).get("/leaderboard")

	assert_html(r, 200)
	section = _board(r, "blocked")
	assert section.index(thrice["username"]) < section.index(twice["username"]) < section.index(once["username"])


def test_blocked_board_leaves_out_users_nobody_blocks():
	blocked, blocker = factories.user(), factories.user()
	_block(blocker, blocked)

	r = as_user(factories.admin(2)).get("/leaderboard")

	assert_html(r, 200)
	section = _board(r, "blocked")
	assert blocked["username"] in section
	assert blocker["username"] not in section


def test_blocked_board_lists_25_users():
	targets = [factories.user() for _ in range(26)]
	blockers = [factories.user() for _ in range(26)]
	for rank, target in enumerate(targets):
		for blocker in blockers[:26 - rank]:
			_block(blocker, target)

	r = as_user(factories.admin(2)).get("/leaderboard")

	assert_html(r, 200)
	section = _board(r, "blocked")
	for target in targets[:25]:
		assert target["username"] in section, target["username"]
	assert targets[25]["username"] not in section


def test_blocked_board_adds_the_viewers_row_when_nobody_blocks_them():
	blocked = factories.user()
	_block(factories.user(), blocked)
	viewer = factories.admin(2)

	r = as_user(viewer).get("/leaderboard")

	assert_html(r, 200)
	section = _board(r, "blocked")
	assert _rows_of(section, viewer) == _rows_of(section, blocked) > 0


def test_blocked_board_shows_a_listed_viewer_once():
	viewer, peer = factories.admin(2), factories.user()
	_block(factories.user(), viewer)
	_block(factories.user(), peer)

	r = as_user(viewer).get("/leaderboard")

	assert_html(r, 200)
	section = _board(r, "blocked")
	assert _rows_of(section, viewer) == _rows_of(section, peer) > 0


# The precomputed boards

def _downvoted(times):
	'''A user whose one post received `times` downvotes.'''
	target = factories.user()
	post = factories.post(target)
	for _ in range(times):
		db.insert("votes", user_id=factories.user()["id"], submission_id=post["id"], vote_type=-1)
	return target, post


def _upvoter(times):
	'''A user who upvoted `times` posts (beyond the self-votes posting leaves).'''
	voter = factories.user()
	for _ in range(times):
		db.insert("votes", user_id=voter["id"], submission_id=factories.post(factories.user())["id"], vote_type=1)
	return voter


def test_precomputed_boards_are_left_out_until_computed():
	r = as_user(factories.admin(2)).get("/leaderboard")

	assert_html(r, 200)
	assert not _has_board(r, "received-downvotes")
	assert not _has_board(r, "given-upvotes")


def test_precomputed_boards_show_once_computed():
	target, _ = _downvoted(3)
	voter = _upvoter(3)

	assert_cli_ok(cli("leaderboard_recalc"))
	r = as_user(factories.admin(2)).get("/leaderboard")

	assert_html(r, 200)
	assert target["username"] in _board(r, "received-downvotes")
	assert voter["username"] in _board(r, "given-upvotes")


def test_precomputed_boards_count_comment_votes():
	target, voter = factories.user(), factories.user()
	comment = factories.comment(target, factories.post(factories.user()))
	db.insert("commentvotes", user_id=voter["id"], comment_id=comment["id"], vote_type=-1)
	for _ in range(3):
		db.insert("commentvotes", user_id=factories.user()["id"], comment_id=comment["id"], vote_type=-1)
	upvoter = factories.user()
	for _ in range(3):
		db.insert("commentvotes", user_id=upvoter["id"], comment_id=factories.comment(factories.user(), factories.post(factories.user()))["id"], vote_type=1)

	assert_cli_ok(cli("leaderboard_recalc"))
	r = as_user(factories.admin(2)).get("/leaderboard")

	assert_html(r, 200)
	assert target["username"] in _board(r, "received-downvotes")
	assert upvoter["username"] in _board(r, "given-upvotes")


def test_precomputed_boards_rank_highest_first():
	low, _ = _downvoted(2)
	high, _ = _downvoted(4)
	middle, _ = _downvoted(3)
	few, many = _upvoter(2), _upvoter(4)

	assert_cli_ok(cli("leaderboard_recalc"))
	r = as_user(factories.admin(2)).get("/leaderboard")

	assert_html(r, 200)
	section = _board(r, "received-downvotes")
	assert section.index(high["username"]) < section.index(middle["username"]) < section.index(low["username"])
	section = _board(r, "given-upvotes")
	assert section.index(many["username"]) < section.index(few["username"])


def test_precomputed_boards_reflect_votes_as_of_the_last_computation():
	assert_cli_ok(cli("leaderboard_recalc"))
	target, _ = _downvoted(3)

	r = as_user(factories.admin(2)).get("/leaderboard")

	assert_html(r, 200)
	assert target["username"] not in _board(r, "received-downvotes")


def test_precomputed_boards_drop_users_deleted_since():
	target, post = _downvoted(3)
	assert_cli_ok(cli("leaderboard_recalc"))
	db.delete("votes", submission_id=post["id"])
	db.delete("submissions", id=post["id"])
	db.delete("users", id=target["id"])

	r = as_user(factories.admin(2)).get("/leaderboard")

	assert_html(r, 200)
	assert target["username"] not in _board(r, "received-downvotes")
