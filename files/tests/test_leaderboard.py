"""Tests for leaderboard classes."""
from . import util_accounts
from . import util_submissions
from . import util_comments

from files.__main__ import db_session
from files.classes import User, Badge, UserBlock, Comment, Submission
from files.classes.leaderboard import (
	LeaderboardMeta,
	SimpleLeaderboard,
	BadgeMarseyLeaderboard,
	UserBlockLeaderboard,
	ReceivedDownvotesLeaderboard,
	GivenUpvotesLeaderboard,
)

def test_simple_leaderboard_basic():
	"""Test SimpleLeaderboard with basic user query."""
	client, user = util_accounts.create_test_client_and_user()

	# Create leaderboard for coins
	meta = LeaderboardMeta("Coins", "coins", "coins", "Coins", None)
	users_query = db_session.query(User)
	lb = SimpleLeaderboard(user, meta, db_session, users_query, User.coins)

	# Check basic properties
	assert lb.v == user
	assert lb.meta == meta
	assert isinstance(lb.all_users, list)
	assert len(lb.all_users) <= meta.limit

	# Check value_func works
	if len(lb.all_users) > 0:
		first_user = lb.all_users[0]
		value = lb.value_func(first_user)
		assert isinstance(value, int)
		assert value == first_user.coins

def test_simple_leaderboard_user_not_in_top():
	"""Test SimpleLeaderboard when viewing user is not in top rankings."""
	# Create a user with low coins
	client, low_coin_user = util_accounts.create_test_client_and_user("lb-low-coin")

	# Set their coins to 0 to ensure they're at the bottom
	low_coin_user.coins = 0
	db_session.commit()

	# Create leaderboard with small limit and filter for users with positive coins
	meta = LeaderboardMeta("Coins", "coins", "coins", "Coins", None, limit=5)
	users_query = db_session.query(User).filter(User.coins > 0)
	lb = SimpleLeaderboard(low_coin_user, meta, db_session, users_query, User.coins)

	# Since low_coin_user has 0 coins and query filters for > 0, they won't be in results
	# The leaderboard should handle this gracefully by calculating their position
	# The _calculate method will query for this user's position even if they don't match the filter
	assert isinstance(lb.all_users, list)
	# v_position and v_value are only set if user is not in all_users
	if low_coin_user not in lb.all_users:
		assert lb.v_position > len(lb.all_users)
		assert lb.v_value == 0

def test_simple_leaderboard_user_in_top():
	"""Test SimpleLeaderboard when viewing user is in top rankings."""
	from sqlalchemy import func

	client, user = util_accounts.create_test_client_and_user("lb-top-user")

	# Give user more coins than anyone else to ensure they're #1
	max_coins = db_session.query(func.max(User.coins)).scalar() or 0
	user.coins = max_coins + 1000000
	db_session.commit()

	# Create leaderboard
	meta = LeaderboardMeta("Coins", "coins", "coins", "Coins", None)
	users_query = db_session.query(User)
	lb = SimpleLeaderboard(user, meta, db_session, users_query, User.coins)

	# User should be in all_users (top 25) since they have the most coins
	assert user in lb.all_users
	# When user is in top rankings, v_position and v_value should be None
	assert lb.v_position is None
	assert lb.v_value is None

def test_badge_marsey_leaderboard_badges():
	"""Test BadgeMarseyLeaderboard with Badge.user_id."""
	client, user = util_accounts.create_test_client_and_user("lb-badge-user")

	# Create some badges for the user
	from files.classes.badges import Badge
	badge1 = Badge(user_id=user.id, badge_id=1, description="Test Badge 1")
	badge2 = Badge(user_id=user.id, badge_id=2, description="Test Badge 2")
	db_session.add(badge1)
	db_session.add(badge2)
	db_session.commit()

	# Create leaderboard
	meta = LeaderboardMeta("Badges", "badges", "badges", "Badges", None)
	lb = BadgeMarseyLeaderboard(user, meta, db_session, Badge.user_id)

	# Check basic properties
	assert isinstance(lb.all_users, list)
	assert isinstance(lb.v_position, int)
	assert isinstance(lb.v_value, int)

	# User should have at least 2 badges
	if user in lb.all_users:
		assert lb.value_func(user) >= 2

def test_badge_marsey_leaderboard_user_with_no_badges():
	"""Test BadgeMarseyLeaderboard when viewing user has no badges."""
	client, user = util_accounts.create_test_client_and_user("lb-no-badge-user")

	# Don't create any badges for this user

	# Create leaderboard
	meta = LeaderboardMeta("Badges", "badges", "badges", "Badges", None)
	lb = BadgeMarseyLeaderboard(user, meta, db_session, Badge.user_id)

	# User should not be in top users (assuming other users have badges)
	# But should have position and value of 0
	assert isinstance(lb.v_position, int)
	assert isinstance(lb.v_value, int)

def test_userblock_leaderboard_basic():
	"""Test UserBlockLeaderboard with basic blocking."""
	client1, blocker1 = util_accounts.create_test_client_and_user("blocker-1")
	client2, blocker2 = util_accounts.create_test_client_and_user("blocker-2")
	client3, blocked_user = util_accounts.create_test_client_and_user("blocked-user")

	# Create blocks targeting blocked_user
	block1 = UserBlock(user_id=blocker1.id, target_id=blocked_user.id)
	block2 = UserBlock(user_id=blocker2.id, target_id=blocked_user.id)
	db_session.add(block1)
	db_session.add(block2)
	db_session.commit()

	# Create leaderboard
	meta = LeaderboardMeta("Blocked", "most blocked", "blocked", "Blocked By", "blockers")
	lb = UserBlockLeaderboard(blocked_user, meta, db_session, UserBlock.target_id)

	# Check basic properties
	assert isinstance(lb.all_users, list)
	assert isinstance(lb.v_position, int)
	assert isinstance(lb.v_value, int)

	# blocked_user should have at least 2 blocks
	if blocked_user in lb.all_users:
		assert lb.value_func(blocked_user) >= 2

def test_userblock_leaderboard_user_not_blocked():
	"""Test UserBlockLeaderboard when viewing user has no blocks."""
	client, user = util_accounts.create_test_client_and_user("unblocked-user")

	# Don't create any blocks for this user

	# Create leaderboard
	meta = LeaderboardMeta("Blocked", "most blocked", "blocked", "Blocked By", "blockers")
	lb = UserBlockLeaderboard(user, meta, db_session, UserBlock.target_id)

	# User should not be in top users (assuming other users are blocked)
	# But should have position and value
	assert isinstance(lb.v_position, int)
	assert isinstance(lb.v_value, int)
	assert lb.v_value == 0

def test_received_downvotes_leaderboard():
	"""Test ReceivedDownvotesLeaderboard."""
	# Create users and content
	client1, author = util_accounts.create_test_client_and_user("downvote-author")
	client2, downvoter = util_accounts.create_test_client_and_user("downvoter")

	# Create a post and downvote it
	post = util_submissions.create_submission_for_client(client1)

	# Downvote the post
	from . import util
	downvote_response, _ = util.post_with_formkey(
		client2, f"/vote/post/{post.id}/-1",
		data={}
	)

	# Create leaderboard
	meta = LeaderboardMeta("Downvotes", "received downvotes", "received-downvotes", "downvotes", "downvoted")
	lb = ReceivedDownvotesLeaderboard(meta, db_session)

	# Check basic properties (note: v is None for RawSqlLeaderboard)
	assert lb.v is None
	assert isinstance(lb.all_users, list)
	assert lb.v_position is None
	assert lb.v_value is None
	assert lb.v_appears_in_ranking is True  # Always True for RawSqlLeaderboard

	# Check that value_func works for users in the result
	if len(lb.all_users) > 0:
		first_user = lb.all_users[0]
		value = lb.value_func(first_user)
		assert isinstance(value, int)
		assert value >= 0

def test_given_upvotes_leaderboard():
	"""Test GivenUpvotesLeaderboard."""
	# Create users and content
	client1, author = util_accounts.create_test_client_and_user("upvote-author")
	client2, upvoter = util_accounts.create_test_client_and_user("upvoter")

	# Create a post and upvote it
	post = util_submissions.create_submission_for_client(client1)

	# Upvote the post
	from . import util
	upvote_response, _ = util.post_with_formkey(
		client2, f"/vote/post/{post.id}/1",
		data={}
	)

	# Create leaderboard
	meta = LeaderboardMeta("Upvotes", "given upvotes", "given-upvotes", "upvotes", "upvoting")
	lb = GivenUpvotesLeaderboard(meta, db_session)

	# Check basic properties (note: v is None for RawSqlLeaderboard)
	assert lb.v is None
	assert isinstance(lb.all_users, list)
	assert lb.v_position is None
	assert lb.v_value is None
	assert lb.v_appears_in_ranking is True

	# Check that value_func works for users in the result
	if len(lb.all_users) > 0:
		first_user = lb.all_users[0]
		value = lb.value_func(first_user)
		assert isinstance(value, int)
		assert value >= 0

def test_leaderboard_meta_dataclass():
	"""Test LeaderboardMeta dataclass properties."""
	meta = LeaderboardMeta(
		"Test Header",
		"test table header",
		"test-id",
		"Test Column",
		"/test/url"
	)

	assert meta.header_name == "Test Header"
	assert meta.table_header_name == "test table header"
	assert meta.html_id == "test-id"
	assert meta.table_column_name == "Test Column"
	assert meta.user_relative_url == "/test/url"
	assert meta.limit == 25  # Default LEADERBOARD_LIMIT

def test_leaderboard_meta_custom_limit():
	"""Test LeaderboardMeta with custom limit."""
	meta = LeaderboardMeta(
		"Test",
		"test",
		"test",
		"Test",
		None,
		limit=10
	)

	assert meta.limit == 10

def test_simple_leaderboard_with_different_columns():
	"""Test SimpleLeaderboard with different user columns."""
	client, user = util_accounts.create_test_client_and_user("lb-multi-col")

	# Test with post_count
	meta_posts = LeaderboardMeta("Posts", "posts", "posts", "Posts", None)
	users_query = db_session.query(User)
	lb_posts = SimpleLeaderboard(user, meta_posts, db_session, users_query, User.post_count)

	assert isinstance(lb_posts.all_users, list)

	# Test with comment_count
	meta_comments = LeaderboardMeta("Comments", "comments", "comments", "Comments", None)
	lb_comments = SimpleLeaderboard(user, meta_comments, db_session, users_query, User.comment_count)

	assert isinstance(lb_comments.all_users, list)

def test_leaderboard_v_appears_in_ranking():
	"""Test v_appears_in_ranking property."""
	# Create user with very low coins so they're not in ranking
	client, user = util_accounts.create_test_client_and_user("lb-appears")
	user.coins = 1
	db_session.commit()

	meta = LeaderboardMeta("Coins", "coins", "coins", "Coins", None, limit=5)
	users_query = db_session.query(User).filter(User.coins > 0)
	lb = SimpleLeaderboard(user, meta, db_session, users_query, User.coins)

	# Test that v_appears_in_ranking works correctly
	# If user is not in all_users, v_position will be set and v_appears_in_ranking should work
	if user not in lb.all_users:
		# v_appears_in_ranking checks if v_position <= len(all_users)
		# Since user is not in top, their position should be > len(all_users)
		assert lb.v_appears_in_ranking is False