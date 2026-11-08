'''
Each time the scheduled-task worker runs a task, it records the run in `tasks_repeatable_runs`: `created_utc` when it started, `completed_utc` when it finished, and in `traceback_str` the details of what went wrong, or NULL when nothing did. A run whose details aren't empty failed. A failure is logged and recorded, the task waits for its next slot as after any run, and the worker goes on to the other due tasks. Whatever a failing job had committed before it failed stays.

While it runs, a task is marked running (`run_state` 2, else 1, waiting). When the worker starts, a task still marked running was interrupted by a worker that stopped: its unfinished run is recorded as failed, completed when the new worker started, and the task waits again. The interrupted run used up its slot, so the task runs again at its next slot, not at once.

A job task (`tasks_repeatable_python`) names the job it runs by `import_path` and `callable`; one naming no job the site has fails every run.
'''
import calendar
from datetime import datetime, timedelta, timezone

import pytest

from files.tests.spec.harness import *

MONDAY = 1 << 2
SLOT = datetime(2024, 1, 8, 8, 0, tzinfo=timezone.utc)
'''A Monday 08:00 UTC.'''
CREATED = calendar.timegm((2024, 1, 2, 0, 0, 0))
'''A Tuesday, after the Monday slot before SLOT.'''


def _epoch(at: datetime) -> int:
	return calendar.timegm(at.utctimetuple())


def _due(task_factory, *args, **overrides):
	return task_factory(*args, frequency_day=MONDAY, time_of_day_utc="08:00", created_utc=CREATED, **overrides)


def _missing_job(admin):
	token = factories.unique("job")
	return _due(factories.job, admin, f"files.nonexistent_{token}", "run"), token


def test_a_job_naming_a_callable_its_module_lacks_fails():
	job = _due(factories.job, factories.admin(2), "files.commands.leaderboard_recalc", factories.unique("callable"))

	run_scheduler(SLOT)

	[run] = db.rows("tasks_repeatable_runs", task_id=job["id"])
	assert run["traceback_str"]


def test_a_run_records_when_it_started_and_finished():
	scheduled = _due(factories.scheduled_post, factories.admin(2))

	run_scheduler(SLOT)

	[run] = db.rows("tasks_repeatable_runs", task_id=scheduled["id"])
	assert (run["created_utc"], run["completed_utc"], run["traceback_str"], run["manual"]) == (_epoch(SLOT), SLOT.replace(tzinfo=None), None, False)


def test_a_failed_run_is_recorded_with_its_details():
	job, token = _missing_job(factories.admin(2))

	run_scheduler(SLOT)

	[run] = db.rows("tasks_repeatable_runs", task_id=job["id"])
	assert (run["created_utc"], run["completed_utc"]) == (_epoch(SLOT), SLOT.replace(tzinfo=None))
	assert token in run["traceback_str"]
	assert db.row("tasks_repeatable", id=job["id"])["run_state"] == 1


@pytest.mark.parametrize("level, shown", [(2, False), (3, True)])
def test_a_failed_runs_details_are_shown_to_head_admins(level, shown):
	job, token = _missing_job(factories.admin(2))
	run_scheduler(SLOT)
	[run] = db.rows("tasks_repeatable_runs", task_id=job["id"])

	r = as_user(factories.admin(level)).get(f"/tasks/{job['id']}/runs/{run['id']}")

	assert_html(r, 200)
	(assert_in_payload if shown else assert_not_in_payload)(r, token)


def test_a_failed_task_waits_for_its_next_slot():
	job, _ = _missing_job(factories.admin(2))

	run_scheduler(SLOT)
	run_scheduler(SLOT + timedelta(minutes=1))
	after_first_slot = len(db.rows("tasks_repeatable_runs", task_id=job["id"]))
	run_scheduler(SLOT + timedelta(days=7))

	runs = db.rows("tasks_repeatable_runs", task_id=job["id"])
	assert (after_first_slot, len(runs), all(r["traceback_str"] for r in runs)) == (1, 2, True)


def test_a_failure_doesnt_stop_the_other_due_tasks():
	admin = factories.admin(2)
	# Failing jobs made both before and after it, so one fails ahead of it whichever order the worker takes them in
	_missing_job(admin)
	scheduled = _due(factories.scheduled_post, admin)
	_missing_job(admin)

	run_scheduler(SLOT)

	assert len(db.rows("submissions", task_id=scheduled["id"])) == 1
	assert [r["traceback_str"] is None for r in db.rows("tasks_repeatable_runs", task_id=scheduled["id"])] == [True]


def test_a_task_interrupted_by_a_stopped_worker_is_recorded_as_failed_and_waits_for_its_next_slot():
	scheduled = _due(factories.scheduled_post, factories.admin(2), run_state=2, run_time_last=SLOT.replace(tzinfo=None))
	run = factories.task_run(scheduled, created_utc=_epoch(SLOT), completed_utc=None)
	restart = SLOT + timedelta(hours=1)

	with db_diff() as d:
		run_scheduler(restart)

	d.assert_exactly(updated={
		"tasks_repeatable": {scheduled["id"]: {"run_state": 1}},
		"tasks_repeatable_runs": {run["id"]: {"completed_utc": restart.replace(tzinfo=None), "traceback_str": ANY}},
	})
	assert db.row("tasks_repeatable_runs", id=run["id"])["traceback_str"]

	run_scheduler(SLOT + timedelta(days=7))

	assert len(db.rows("submissions", task_id=scheduled["id"])) == 1
