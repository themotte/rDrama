'''
The migration that adds `tasks_repeatable.schedule_changed_utc` fills it in for existing tasks with when they were created, in UTC whatever the database session's time zone. The suite's database is migrated empty, so its data step is checked here.
'''
import importlib.util
import pathlib
from datetime import datetime

from files.tests.spec.harness import db, db_diff, factories

_PATH = next(pathlib.Path(__file__).parents[3].glob("migrations/versions/*_task_schedule_changed_utc.py"))


def _backfill_sql():
	spec = importlib.util.spec_from_file_location("schedule_changed_migration", _PATH)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module.BACKFILL_SQL


def test_existing_tasks_count_their_schedule_as_set_when_they_were_created():
	task = factories.job(factories.admin(2), "files.helpers.config.const", "nothing", created_utc=1_700_000_000, schedule_changed_utc=datetime(2000, 1, 1))

	with db_diff() as d:
		db.execute(f"SET LOCAL TIME ZONE 'America/New_York'; {_backfill_sql()}")

	d.assert_exactly(updated={"tasks_repeatable": {task["id"]: {"schedule_changed_utc": datetime(2023, 11, 14, 22, 13, 20)}}})
