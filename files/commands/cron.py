import contextlib
import logging
import time
from datetime import datetime, timezone
from typing import Final

from sqlalchemy.orm import scoped_session, Session

from files.__main__ import app, db_session
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


@app.cli.command(_CRON_COMMAND_NAME)
def cron_app_worker():
	'''
	The "worker" process task. This actually executes tasks.
	'''

	# someday we'll clean this up further, for now I need debug info
	logging.basicConfig(level=logging.INFO)

	logging.info("Starting scheduler worker process")
	while True:
		try:
			_run_tasks(db_session)
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
	db.execute(f"LOCK TABLE {table} IN ACCESS EXCLUSIVE MODE")
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


def _run_tasks(db_session_factory: scoped_session):
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

		db.begin()
		run: RepeatableTaskRun = task.run(db, task.run_time_last_or_created_utc)
		task_debug_identifier = f"(ID {run.task_id}:{task.label}, run ID {run.id})"
		logging.info(f"Running task {task_debug_identifier}")
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
