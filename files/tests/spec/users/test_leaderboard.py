'''
GET /leaderboard, for admins of level 2 (anonymous browsers are sent to log in; lower levels and API clients are refused with 403).

The page shows several boards, each a section whose element id is "leaderboard-<board>":
- "truescore", "followers", "posts", "comments": the 25 users with the highest truescore, follower count, post count and comment count, highest first.
- "blocked": the 25 users blocked by the most users, most blocked first; users nobody blocks aren't ranked.
- "received-downvotes" and "given-upvotes": the 25 users who received the most downvotes, and who gave the most upvotes, on posts and comments. These are expensive to compute, so the `leaderboard_recalc` command computes them ahead of time; until it has run, and again after the cache is dumped (admin/test_dashboard.py), the page leaves both out.

Users tied on a board are listed oldest account (lowest id) first. The page opens with links to each board (#leaderboard-<board>). Each row's count links to the list it counts, where there is one the viewer may open: the user's followers, posts (/@<username>/posts) or comments (/@<username>/), and for admins of level 3, the voter lists behind the precomputed boards (/@<username>/downvoters, /@<username>/upvoting). The viewing admin's own row (with their own count, written with thousands separators) is added after a board's list when they aren't in it (on the blocked board, also when nobody blocks them).

Shadowbanned users are ranked like anyone else, and their rows name who shadowbanned them.
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
	'''The text of one board.'''
	return element_text(r, f"leaderboard-{board}")


def _board_links(r, board) -> list[str]:
	return links(r, within=f"leaderboard-{board}")


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
def test_simple_boards_viewer_row_gives_the_viewers_own_count(board, column):
	[_ranked(column, HIGH + i) for i in range(25)]
	viewer = factories.admin(2, **{column: 123_457})

	r = as_user(viewer).get("/leaderboard")

	assert_html(r, 200)
	assert "123,457" in _board(r, board)


@pytest.mark.parametrize("board, column", SIMPLE_BOARDS.items())
def test_simple_board_shows_a_listed_viewer_once(board, column):
	viewer = factories.admin(2, **{column: HIGH + 1})
	peer = _ranked(column, HIGH)

	r = as_user(viewer).get("/leaderboard")

	assert_html(r, 200)
	section = _board(r, board)
	assert _rows_of(section, viewer) == _rows_of(section, peer) > 0


@pytest.mark.parametrize("board, column", SIMPLE_BOARDS.items())
def test_simple_board_adds_the_viewers_row_when_a_tie_leaves_them_out(board, column):
	listed = [_ranked(column, HIGH) for _ in range(25)]
	viewer = factories.admin(2, **{column: HIGH})

	r = as_user(viewer).get("/leaderboard")

	assert_html(r, 200)
	section = _board(r, board)
	assert _rows_of(section, viewer) == _rows_of(section, listed[0]) > 0


def _touch_in_reverse(users):
	'''Rewrites each user's row, last-created first, so storage order no longer follows creation order.'''
	for user in reversed(users):
		db.update("users", {"id": user["id"]}, bio=factories.unique())


def _in_order(section, users) -> bool:
	positions = [section.index(user["username"]) for user in users]
	return positions == sorted(positions)


@pytest.mark.parametrize("board, column", SIMPLE_BOARDS.items())
def test_simple_board_breaks_ties_by_account_age(board, column):
	tied = [_ranked(column, HIGH) for _ in range(4)]
	_touch_in_reverse(tied)

	r = as_user(factories.admin(2)).get("/leaderboard")

	assert_html(r, 200)
	assert _in_order(_board(r, board), tied)


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


def test_blocked_board_breaks_ties_by_account_age():
	tied = [factories.user() for _ in range(4)]
	for target in reversed(tied):
		_block(factories.user(), target)
		_block(factories.user(), target)
	_touch_in_reverse(tied)

	r = as_user(factories.admin(2)).get("/leaderboard")

	assert_html(r, 200)
	assert _in_order(_board(r, "blocked"), tied)


def test_blocked_board_adds_the_viewers_row_when_a_tie_leaves_them_out():
	listed = [factories.user() for _ in range(25)]
	viewer = factories.admin(2)
	for target in listed + [viewer]:
		_block(factories.user(), target)

	r = as_user(viewer).get("/leaderboard")

	assert_html(r, 200)
	section = _board(r, "blocked")
	assert _rows_of(section, viewer) == _rows_of(section, listed[0]) > 0


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


def test_dumping_the_cache_leaves_the_precomputed_boards_out_until_computed_again():
	_downvoted(3)
	assert_cli_ok(cli("leaderboard_recalc"))
	admin = as_user(factories.admin(2))
	assert_json_message(admin.post("/admin/dump_cache"))

	r = admin.get("/leaderboard")

	assert_html(r, 200)
	assert not _has_board(r, "received-downvotes")
	assert not _has_board(r, "given-upvotes")


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


def test_precomputed_boards_break_ties_by_account_age():
	downvoted = [_downvoted(3)[0] for _ in range(4)]
	upvoters = [_upvoter(3) for _ in range(4)]
	_touch_in_reverse(downvoted + upvoters)

	assert_cli_ok(cli("leaderboard_recalc"))
	r = as_user(factories.admin(2)).get("/leaderboard")

	assert_html(r, 200)
	assert _in_order(_board(r, "received-downvotes"), downvoted)
	assert _in_order(_board(r, "given-upvotes"), upvoters)


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


# Where rows lead

@pytest.mark.parametrize("board, column, page", [("followers", "stored_subscriber_count", "followers"), ("posts", "post_count", "posts")])
def test_simple_board_rows_link_to_the_counted_list(board, column, page):
	user = _ranked(column, HIGH)

	r = as_user(factories.admin(2)).get("/leaderboard")

	assert_html(r, 200)
	assert f"/@{user['username']}/{page}" in _board_links(r, board)


@pytest.mark.parametrize("board, column", SIMPLE_BOARDS.items())
def test_boards_link_to_no_missing_pages(board, column):
	user = _ranked(column, HIGH)
	for _ in range(2):
		_block(factories.user(), user)

	r = as_user(factories.admin(2)).get("/leaderboard")

	assert_html(r, 200)
	for missing in ("comments", "blockers", "downvoted"):
		assert f"/@{user['username']}/{missing}" not in r.text


def test_precomputed_boards_link_level_3_admins_to_the_voter_lists():
	downvoted, _ = _downvoted(3)
	upvoter = _upvoter(3)
	assert_cli_ok(cli("leaderboard_recalc"))

	r = as_user(factories.admin(3)).get("/leaderboard")

	assert_html(r, 200)
	assert f"/@{downvoted['username']}/downvoters" in _board_links(r, "received-downvotes")
	assert f"/@{upvoter['username']}/upvoting" in _board_links(r, "given-upvotes")


def test_precomputed_boards_dont_link_level_2_admins_to_the_voter_lists():
	downvoted, _ = _downvoted(3)
	upvoter = _upvoter(3)
	assert_cli_ok(cli("leaderboard_recalc"))

	r = as_user(factories.admin(2)).get("/leaderboard")

	assert_html(r, 200)
	assert f"/@{downvoted['username']}/downvoters" not in r.text
	assert f"/@{upvoter['username']}/upvoting" not in r.text
	assert f"/@{downvoted['username']}/downvoted" not in r.text


def test_leaderboard_links_to_each_board():
	_downvoted(1)
	assert_cli_ok(cli("leaderboard_recalc"))

	r = as_user(factories.admin(2)).get("/leaderboard")

	assert_html(r, 200)
	for board in [*SIMPLE_BOARDS, "blocked", "received-downvotes", "given-upvotes"]:
		assert f'href="#leaderboard-{board}"' in r.text, board


# Shadowbanned users

def test_a_shadowbanned_users_row_names_who_shadowbanned_them():
	shadowbanner, reason = factories.unique(), factories.unique()
	shadowbanned = factories.user(truescore=HIGH + 1, shadowbanned=shadowbanner, ban_reason=reason)

	r = as_user(factories.admin(2)).get("/leaderboard")

	assert_html(r, 200)
	assert shadowbanned["username"] in _board(r, "truescore")
	# The row's tooltip
	assert f"@{shadowbanner}" in element_html(r, "leaderboard-truescore")
	assert_not_in_payload(r, reason)
