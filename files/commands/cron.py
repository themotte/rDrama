import contextlib
import logging
import time
from datetime import datetime, timezone
from typing import Final, Optional

from sqlalchemy.orm import scoped_session

from files.__main__ import app, db_session
from files.classes.cron.scheduler import (RepeatableTask, RepeatableTaskRun,
                                          ScheduledTaskState)

CRON_SLEEP: Final[int] = 15
'''
How long the app will sleep for between runs. Lower values give better 
resolution, but will hit the database more.
'''

@app.cli.command('cron')
def cron_app():
	db:scoped_session = db_session() # type: ignore
	while True:
		_run_tasks(db)
		time.sleep(CRON_SLEEP)


@contextlib.contextmanager
def _acquire_exclusive_lock(db:scoped_session, table:str):
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

	with _acquire_exclusive_lock(db, "tasks_repeatable"):
		tasks:list[RepeatableTask] = db.query(RepeatableTask).filter(
			RepeatableTask.enabled == True,
			RepeatableTask.run_state != int(ScheduledTaskState.RUNNING)).all()

	now:datetime = datetime.now(tz=timezone.utc)
	for task in tasks:
		trigger_time:Optional[datetime] = \
			task.next_trigger(task.run_time_last_or_created_utc)

		with _acquire_exclusive_lock(db, "tasks_repeatable"):
			if not trigger_time: continue
			if now < trigger_time: continue
			task.run_time_last = now
			task.run_state_enum = ScheduledTaskState.RUNNING
		
		run:RepeatableTaskRun = task.run(db, task.run_time_last_or_created_utc)
		if run.exception:
			logging.exception(
				f"Exception running task (ID {run.task_id}, run ID {run.id})", 
				exc_info=run.exception
			)
		with _acquire_exclusive_lock(db, "tasks_repeatable"):
			task.run_state_enum = ScheduledTaskState.WAITING
	db.commit()
