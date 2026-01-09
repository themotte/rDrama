import contextlib
import logging
import time
from datetime import datetime, timezone
from typing import Final

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker, Session

from files.__main__ import app, db_session_factory
from files.classes.cron.tasks import (DayOfWeek, RepeatableTask,
                                      RepeatableTaskRun, ScheduledTaskState)

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


def _recover_stuck_tasks(db_session_factory: sessionmaker):
	'''
	Recovers tasks that are stuck in RUNNING state (e.g., due to server crash).
	Also marks any orphaned task runs (with no completed_utc) as failed.

	This should be called once at startup before the main loop begins.
	No exclusive lock is needed since this runs before the main loop starts.
	'''
	db: Session = db_session_factory()

	# Reset any tasks stuck in RUNNING state using a bulk update
	stuck_count = db.query(RepeatableTask).filter(
		RepeatableTask.run_state == int(ScheduledTaskState.RUNNING)
	).update({RepeatableTask.run_state: int(ScheduledTaskState.WAITING)})

	if stuck_count:
		logging.warning(
			f"Reset {stuck_count} task(s) stuck in RUNNING state to WAITING."
		)

	# Mark orphaned runs as failed (runs that never completed)
	now = datetime.now(tz=timezone.utc)
	orphan_count = db.query(RepeatableTaskRun).filter(
		RepeatableTaskRun.completed_utc == None
	).update({
		RepeatableTaskRun.completed_utc: now,
		RepeatableTaskRun.traceback_str: "Task was interrupted by server shutdown"
	})

	if orphan_count:
		logging.warning(
			f"Marked {orphan_count} orphaned task run(s) as failed."
		)

	db.commit()


@app.cli.command(_CRON_COMMAND_NAME)
def cron_app_worker():
	'''
	The "worker" process task. This actually executes tasks.
	'''

	# someday we'll clean this up further, for now I need debug info
	logging.basicConfig(level=logging.INFO)

	logging.info("Starting scheduler worker process")

	# Recover any tasks stuck from a previous crash
	try:
		_recover_stuck_tasks(db_session_factory)
	except Exception as e:
		logging.exception("Failed to recover stuck tasks", exc_info=e)

	while True:
		try:
			_run_tasks(db_session_factory)
		except Exception as e:
			logging.exception(
				"An unhandled exception occurred while running tasks",
				exc_info=e
			)
		time.sleep(CRON_SLEEP_SECONDS)


@contextlib.contextmanager
def _acquire_lock_exclusive(db: Session, table: str):
	'''
	Acquires an exclusive lock on the table provided by the `table` parameter.
	This can be used for synchronizing the state of the specified table and 
	making sure no readers can access it while in the critical section.
	''' 
	# TODO: make `table` the type LiteralString once we upgrade to python 3.11
	db.begin() # we want to raise an exception if there's a txn in progress
	db.execute(text(f"LOCK TABLE {table} IN ACCESS EXCLUSIVE MODE"))
	try:
		yield
		db.commit()
	except Exception:
		logging.error(
			"An exception occurred during an operation in a critical section. "
			"A task might not occur or might be duplicated."
		)
		try:
			db.rollback()
		except:
			logging.warning(
				f"Failed to rollback database. The table {table} might still "
				"be locked.")
		raise


def _run_tasks(db_session_factory: sessionmaker):
	'''
	Runs tasks, attempting to guarantee that a task is ran once and only once.
	This uses postgres to lock the table containing our tasks at key points in
	in the process (reading the tasks and writing the last updated time).

	The task itself is ran outside of this context; this is so that a long
	running task does not lock the entire table for its entire run, which would
	for example, prevent any statistics about status from being gathered.
	'''
	db: Session = db_session_factory()

	with _acquire_lock_exclusive(db, RepeatableTask.__tablename__):
		now: datetime = datetime.now(tz=timezone.utc)

		tasks: list[RepeatableTask] = db.query(RepeatableTask).filter(
			RepeatableTask.enabled == True,
			RepeatableTask.frequency_day != int(DayOfWeek.NONE),
			RepeatableTask.run_state != int(ScheduledTaskState.RUNNING),
			(RepeatableTask.run_time_last <= now)
				| (RepeatableTask.run_time_last == None),
		).all()

		# SQLA needs to query again for the inherited object info anyway
		# so it's fine that objects in the list get expired on txn end.
		# Prefer more queries to risk of task run duplication.
		tasks_to_run: list[RepeatableTask] = list(filter(
			lambda task: task.can_run(now),	tasks))

	for task in tasks_to_run:
		now = datetime.now(tz=timezone.utc)
		with _acquire_lock_exclusive(db, RepeatableTask.__tablename__):
			# We need to check for runnability again because we don't mutex
			# the RepeatableTask.run_state until now.
			if not task.can_run(now):
				continue
			task.run_time_last = now
			task.run_state_enum = ScheduledTaskState.RUNNING

		# This *must* happen before we start doing db queries, including sqlalchemy db queries
		db.begin()
		task_debug_identifier = f"(ID {task.id}:{task.label})"
		logging.info(f"Running task {task_debug_identifier}")

		run: RepeatableTaskRun = task.run(db, task.run_time_last_or_created_utc)

		if run.exception:
			# TODO: collect errors somewhere other than just here and in the 
			# task run object itself (see #220).
			logging.exception(
				f"Exception running task {task_debug_identifier}", 
				exc_info=run.exception
			)
			db.rollback()
		else:
			db.commit()
			logging.info(f"Finished task {task_debug_identifier}")

		with _acquire_lock_exclusive(db, RepeatableTask.__tablename__):
			task.run_state_enum = ScheduledTaskState.WAITING
