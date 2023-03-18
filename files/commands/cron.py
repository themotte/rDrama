import contextlib
import logging
import time
from datetime import datetime, timezone
from typing import Final, Optional

from sqlalchemy.orm import scoped_session

from files.__main__ import app, db_session
from files.classes.cron.scheduler import (DayOfWeek, RepeatableTask,
                                          RepeatableTaskRun,
                                          ScheduledTaskState)

CRON_SLEEP_SECONDS: Final[int] = 15
'''
How long the app will sleep for between runs. Lower values give better 
resolution, but will hit the database more.

The cost of a lower value is potentially higher lock contention. A value below
`0` will raise a `ValueError` (on call to `time.sleep`). A value of `0` is
possible but not recommended.

The sleep time is not guaranteed to be exactly this value (notable, it may be 
slightly longer if the system is very busy)

This value is passed to `time.sleep()`. For more information on that, see
the Python documentation: https://docs.python.org/3/library/time.html
'''

@app.cli.command('cron_master')
def cron_app_master():
	'''
	The "master" process
	'''
	pass

@app.cli.command('cron')
def cron_app():
	'''
	The "worker" process task. This actually executes tasks.
	'''
	db:scoped_session = db_session() # type: ignore
	while True:
		_run_tasks(db)
		time.sleep(CRON_SLEEP_SECONDS)


@contextlib.contextmanager
def _acquire_exclusive_lock(db:scoped_session, table:str): 
	# TODO: make `table` the type LiteralString once we upgrade to python 3.11
	with db.begin_nested() as t:
		db.execute(f"LOCK TABLE {table} IN ACCESS EXCLUSIVE")
		try:
			yield t
			db.commit()
		except:
			try:
				db.rollback()
			except:
				logging.warning(
					f"Failed to rollback database. The table {table} might still be locked.")


def _run_tasks(db:scoped_session):
	'''
	Runs tasks, attempting to guarantee that a task is ran once and only once.
	This uses postgres to lock the table containing our tasks at key points in
	in the process (reading the tasks and writing the last updated time).

	The task itself is ran outside of this context; this is so that a long
	running task does not lock the entire table for its entire run, which would
	for example, prevent any statistics about status from being gathered.
	'''
	now:datetime = datetime.now(tz=timezone.utc)

	with _acquire_exclusive_lock(db, RepeatableTask.__tablename__):	
		tasks:list[RepeatableTask] = db.query(RepeatableTask).filter(
			RepeatableTask.enabled == True,
			RepeatableTask.frequency_day != int(DayOfWeek.NONE),
			RepeatableTask.run_state != int(ScheduledTaskState.RUNNING),
			RepeatableTask.run_time_last <= now).all()

	for task in tasks:
		with _acquire_exclusive_lock(db, RepeatableTask.__tablename__):
			trigger_time:Optional[datetime] = \
				task.next_trigger(task.run_time_last_or_created_utc)
			if not trigger_time: continue
			if now < trigger_time: continue
			task.run_time_last = now
			task.run_state_enum = ScheduledTaskState.RUNNING
		
		run:RepeatableTaskRun = task.run(db, task.run_time_last_or_created_utc)
		if run.exception:
			# TODO: collect errors somewhere other than just here (see #220)
			logging.exception(
				f"Exception running task (ID {run.task_id}, run ID {run.id})", 
				exc_info=run.exception
			)
		with _acquire_exclusive_lock(db, RepeatableTask.__tablename__):
			task.run_state_enum = ScheduledTaskState.WAITING
		db.commit()
