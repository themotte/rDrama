'''
The precomputed leaderboards are refreshed once a day, so what the refresh stores must last until the next one: it must not expire.
'''
from files.__main__ import cache
from files.classes.leaderboard import GivenUpvotesLeaderboard, ReceivedDownvotesLeaderboard
from files.tests.spec.harness import assert_cli_ok, cli


def test_precomputed_leaderboards_are_stored_without_expiry():
	assert_cli_ok(cli("leaderboard_recalc"))

	redis = cache.cache._write_client
	for board in (ReceivedDownvotesLeaderboard, GivenUpvotesLeaderboard):
		key = cache.cache.key_prefix + board.cache_name()
		assert redis.exists(key), key
		assert redis.ttl(key) == -1, f"{key} expires in {redis.ttl(key)}s"
