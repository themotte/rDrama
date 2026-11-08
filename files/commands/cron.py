import calendar
import contextlib
import logging
import time
import traceback
from datetime import datetime, timezone
from typing import Callable, Final, LiteralString

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker, Session

from files.__main__ import app, cache, db_session_factory
from files.classes.cron.tasks import (DayOfWeek, RepeatableTask,
                                      RepeatableTaskRun, ScheduledTaskState,
                                      TaskRunContext)

CRON_SLEEP_SECONDS: Final[int] = 15
'''
How long the app will sleep for between runs. Lower values give better
resolution, but will hit the database more.

The cost of a lower value is potentially higher lock contention. A value below
`0` will raise a `ValueError` (on call to `time.sleep`). A value of `0` is
possible but not recommended.

The sleep time is not guaranteed to be exactly this value (notably, it may be
slightly longer if the system is very busy)

This value is passed to `time.sleep()`. For more information on that, see
the Python documentation: https://docs.python.org/3/library/time.html
'''

_CRON_COMMAND_NAME = "cron"

Clock = Callable[[], datetime]
'''Returns the current time as an aware UTC datetime.'''


def _utc_now() -> datetime:  # pragma: no cover (the worker's real clock; the spec runs the worker's steps on its own)
	return datetime.now(tz=timezone.utc)


def _recover_interrupted(db: Session, at: datetime):
	'''
	Marks waiting again any task still marked running, and records as failed any run that never completed. Exactly one worker runs, one task at a time, so at the start of a pass anything still running was interrupted: by the worker stopping, or by a failure while recording the run.
	'''
	stuck_count = db.query(RepeatableTask).filter(
		RepeatableTask.run_state == int(ScheduledTaskState.RUNNING)
	).update({RepeatableTask.run_state: int(ScheduledTaskState.WAITING)})
	if stuck_count:
		logging.warning(f"Reset {stuck_count} task(s) stuck in RUNNING state to WAITING.")

	orphan_count = db.query(RepeatableTaskRun).filter(
		RepeatableTaskRun.completed_utc == None
	).update({
		RepeatableTaskRun.completed_utc: _naive_utc(at),
		RepeatableTaskRun.traceback_str: "The run was interrupted before it was recorded as finished"
	})
	if orphan_count:
		logging.warning(f"Marked {orphan_count} orphaned task run(s) as failed.")


@app.cli.command(_CRON_COMMAND_NAME)
def cron_app_worker():  # pragma: no cover (the endless worker loop; the spec runs its steps directly)
	'''
	The "worker" process task. This actually executes tasks.
	'''

	# someday we'll clean this up further, for now I need debug info
	logging.basicConfig(level=logging.INFO)

	logging.info("Starting scheduler worker process")

	while True:
		try:
			tasks_run_due(db_session_factory, _utc_now)
		except Exception as e:
			logging.exception(
				"An unhandled exception occurred while running tasks",
				exc_info=e
			)
		time.sleep(CRON_SLEEP_SECONDS)


@contextlib.contextmanager
def _acquire_lock_exclusive(db: Session, table: LiteralString):
	'''
	Acquires an exclusive lock on the table provided by the `table` parameter.
	This can be used for synchronizing the state of the specified table and 
	making sure no readers can access it while in the critical section.
	''' 
	# Raises if a transaction is already in progress; commits on leaving, rolls back on an exception
	with db.begin():
		db.execute(text(f"LOCK TABLE {table} IN ACCESS EXCLUSIVE MODE"))
		yield


def tasks_run_due(db_session_factory: sessionmaker, now: Clock):
	'''
	Runs tasks, attempting to guarantee that a task is ran once and only once.
	This uses postgres to lock the table containing our tasks at key points in
	in the process (reading the tasks and writing the last updated time).

	The task itself is ran outside of this context; this is so that a long
	running task does not lock the entire table for its entire run, which would
	for example, prevent any statistics about status from being gathered.
	'''
	with db_session_factory() as db:
		with _acquire_lock_exclusive(db, RepeatableTask.__tablename__):
			at: datetime = now()
			_recover_interrupted(db, at)
			due_ids: list[int] = [task.id for task in db.query(RepeatableTask).filter(
				RepeatableTask.enabled == True,
				RepeatableTask.frequency_day != int(DayOfWeek.NONE),
				RepeatableTask.run_state != int(ScheduledTaskState.RUNNING),
			).order_by(RepeatableTask.id) if task.can_run(at)]

		for task_id in due_ids:
			_task_run(db_session_factory, db, task_id, now)


def _naive_utc(at: datetime) -> datetime:
	'''`at` as the database's timestamp columns hold it: UTC, without a zone.'''
	return at.astimezone(timezone.utc).replace(tzinfo=None)


def _task_run(db_session_factory: sessionmaker, db: Session, task_id: int, now: Clock):
	'''
	Runs the task if it's still due, recording the run in `db`: it's marked running and the run's start is committed first, the work then runs in a session of its own, and the run's outcome is recorded as the task goes back to waiting.
	'''
	with _acquire_lock_exclusive(db, RepeatableTask.__tablename__):
		task: RepeatableTask = db.get(RepeatableTask, task_id)
		at: datetime = now()
		# Checked again under the lock, as the task's state is only claimed here
		if not task.can_run(at):  # pragma: no cover (only if the task changed since the pass began, as an admin's edit while an earlier task ran)
			return
		task.run_time_last = _naive_utc(at)
		task.run_state_enum = ScheduledTaskState.RUNNING
		run = RepeatableTaskRun(task_id=task_id, created_utc=calendar.timegm(at.utctimetuple()))
		db.add(run)
		db.flush()
		run_id: int = run.id
		task_debug_identifier = f"(ID {task_id}:{task.label})"

	logging.info(f"Running task {task_debug_identifier}")
	failure: str | None = None
	with db_session_factory() as work_db:
		try:
			task = work_db.get(RepeatableTask, task_id)
			task.run_task(TaskRunContext(app=app, cache=cache, db=work_db, trigger_time=_naive_utc(at)))
			work_db.commit()
			logging.info(f"Finished task {task_debug_identifier}")
		except Exception as e:
			work_db.rollback()
			logging.exception(f"Exception running task {task_debug_identifier}")
			failure = "".join(traceback.format_exception(e))

	with _acquire_lock_exclusive(db, RepeatableTask.__tablename__):
		run = db.get(RepeatableTaskRun, run_id)
		run.completed_utc = _naive_utc(now())
		run.traceback_str = failure
		db.get(RepeatableTask, task_id).run_state_enum = ScheduledTaskState.WAITING
