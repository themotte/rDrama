'''
How the scheduled-task worker records failures a job can only cause from inside: an exception without a message, and one raised while committing the job's work. Both are recorded as failed runs with a traceback, and the task waits again.

The jobs are this module's own functions.
'''
import calendar
from datetime import datetime, timezone

import pytest

from files.classes.cron.tasks import RepeatableTaskRun
from files.tests.spec.harness import db, factories, run_scheduler

MONDAY = 1 << 2
SLOT = datetime(2024, 1, 8, 8, 0, tzinfo=timezone.utc)


def raise_without_message(ctx):
	raise RuntimeError()


def fail_when_committed(ctx):
	# A run of a task that doesn't exist: refused by its foreign key only when the work is committed
	ctx.db.add(RepeatableTaskRun(task_id=2_000_000_000))


@pytest.mark.parametrize("callable, shown", [("raise_without_message", "raise_without_message"), ("fail_when_committed", "tasks_repeatable_runs_task_id_fkey")])
def test_a_failure_is_recorded_with_its_traceback(callable, shown):
	job = factories.job(factories.admin(2), __name__, callable, frequency_day=MONDAY, time_of_day_utc="08:00", created_utc=calendar.timegm((2024, 1, 2, 0, 0, 0)))

	run_scheduler(SLOT)

	[run] = db.rows("tasks_repeatable_runs", task_id=job["id"])
	assert run["traceback_str"].startswith("Traceback") and shown in run["traceback_str"]
	assert db.row("tasks_repeatable", id=job["id"])["run_state"] == 1


def test_a_pass_recovers_a_task_left_running_by_an_earlier_pass():
	from files.__main__ import db_session_factory
	from files.commands.cron import tasks_run_due
	job = factories.job(factories.admin(2), __name__, "raise_without_message", frequency_day=MONDAY, time_of_day_utc="08:00", run_state=2, run_time_last=SLOT.replace(tzinfo=None))
	run = factories.task_run(job, completed_utc=None)

	tasks_run_due(db_session_factory, lambda: SLOT)

	assert db.row("tasks_repeatable", id=job["id"])["run_state"] == 1
	assert db.row("tasks_repeatable_runs", id=run["id"])["traceback_str"]
