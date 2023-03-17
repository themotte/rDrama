import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Final, Optional

from sqlalchemy.orm import scoped_session

from files.classes.cron.scheduler import RepeatableTask, RepeatableTaskRun
from files.__main__ import app, db_session

CRON_SLEEP: Final[int] = 15
'''
Resolution of our clock. Lower values give better resolution, but will hit the
database more.
'''

@app.cli.command('cron')
def cron_app():
	db:scoped_session = db_session() # type: ignore
	while True:
		_run_tasks(db)
		time.sleep(CRON_SLEEP)


@contextmanager
def _acquire_exclusive_lock(db:scoped_session, table:str):
	with db.begin_nested():
		db.execute(f"LOCK TABLE {table} IN ACCESS EXCLUSIVE")
		try:
			yield
			db.commit()
		except:
			db.rollback()


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
			RepeatableTask.enabled == True).all()

	now:datetime = datetime.now(tz=timezone.utc)
	for task in tasks:
		trigger_time:Optional[datetime] = \
			task.next_trigger(task.last_run_or_created_utc)

		with _acquire_exclusive_lock(db, "tasks_repeatable"):
			if not trigger_time: continue
			if now < trigger_time: continue
			task.last_run = now
		
		run:RepeatableTaskRun = task.run(db, task.last_run_or_created_utc)
		if run.exception:
			logging.exception(
				f"Exception running task (ID {run.task_id}, run ID {run.id})", 
				exc_info=run.exception
			)
	db.commit()
