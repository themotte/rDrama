'''
The migration that clears flair locks from older versions whose time has passed, run on rows as those versions left them. The suite's database is migrated empty, so its data step is checked here.
'''
import importlib.util
import pathlib
import time

from files.tests.spec.harness import db, db_diff, factories

_PATH = next(pathlib.Path(__file__).parents[3].glob("migrations/versions/*_unlock_expired_flair_locks.py"))


def _upgrade_sql():
	spec = importlib.util.spec_from_file_location("flair_lock_migration", _PATH)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module.UPGRADE_SQL


def test_expired_locks_are_cleared_and_others_kept():
	expired = factories.user(flairchanged=int(time.time()) - 86400)
	factories.user(flairchanged=2147483647)
	factories.user(flairchanged=int(time.time()) + 86400)
	factories.user(flairchanged=None)

	with db_diff() as d:
		db.execute(_upgrade_sql())

	d.assert_exactly(updated={"users": {expired["id"]: {"flairchanged": None}}})
