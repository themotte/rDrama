'''
The seed_db command, a developer tool outside the spec, fills a development database with users, posts, comments and votes.
'''
from files.tests.spec.harness import assert_cli_ok, cli, db

_TABLES = ("users", "submissions", "comments", "votes", "commentvotes")


def _counts() -> dict[str, int]:
	return {table: db.execute(f"SELECT count(*) FROM {table}") for table in _TABLES}


def test_seed_db_fills_the_database():
	before = _counts()

	assert_cli_ok(cli("seed_db"))

	after = _counts()
	assert all(after[table] > before[table] for table in _TABLES), (before, after)
