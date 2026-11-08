'''
Each time the scheduled-task worker runs a task, it records the run in `tasks_repeatable_runs`: `created_utc` when it started, `completed_utc` when it finished, and in `traceback_str` the details of what went wrong, or NULL when nothing did. A run whose details aren't empty failed. A failure is logged and recorded, the task waits for its next slot as after any run, and the worker goes on to the other due tasks. Whatever a failing job had committed before it failed stays.

A job task (`tasks_repeatable_python`) names the job it runs by `import_path` and `callable`; one naming no job the site has fails every run.
'''
import calendar
from datetime import datetime, timezone

from files.tests.spec.harness import *

MONDAY = 1 << 2
SLOT = datetime(2024, 1, 8, 8, 0, tzinfo=timezone.utc)
'''A Monday 08:00 UTC.'''
CREATED = calendar.timegm((2024, 1, 1, 0, 0, 0))


def _due(task_factory, *args, **overrides):
	return task_factory(*args, frequency_day=MONDAY, time_of_day_utc="08:00", created_utc=CREATED, **overrides)


def _missing_job(admin):
	token = factories.unique("job")
	return _due(factories.job, admin, f"files.nonexistent_{token}", "run"), token


def test_a_failed_run_is_recorded_with_its_details():
	job, token = _missing_job(factories.admin(2))

	run_scheduler(SLOT)

	[run] = db.rows("tasks_repeatable_runs", task_id=job["id"])
	assert (run["created_utc"], run["completed_utc"]) == (calendar.timegm(SLOT.utctimetuple()), SLOT.replace(tzinfo=None))
	assert token in run["traceback_str"]
	assert db.row("tasks_repeatable", id=job["id"])["run_state"] == 1


def test_a_failure_doesnt_stop_the_other_due_tasks():
	admin = factories.admin(2)
	job, _ = _missing_job(admin)
	scheduled = _due(factories.scheduled_post, admin)

	run_scheduler(SLOT)

	assert len(db.rows("submissions", task_id=scheduled["id"])) == 1
	assert [r["traceback_str"] is None for r in db.rows("tasks_repeatable_runs", task_id=scheduled["id"])] == [True]
