import contextlib
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Callable, Final, Optional

import psutil
from sqlalchemy import or_
from sqlalchemy.orm import scoped_session

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

MAXIMUM_MEMORY_RSS: Final[int] = 300 * 1024 * 1024
'''
Maximum real memory that can be used by the worker before it gets terminated
by our master process.
'''

_CRON_COMMAND_NAME = "cron"

@app.cli.command('cron_master')
def cron_app_master():
	'''
	The "master" process. This is essentially an application unto itself. It 
	spawns 1 worker child. 
	
	Implementation note: Some code changes would have to be made to get it
	to orchestrate more, although this is both realistically not a concern™
	and also more than one master can be spawned without causing any issues
	as synchronization is provided by the database.

	Ideally this would not just be one function, but making it larger feels
	like overengineering it.
	'''
	
	def _spawn_worker_process():
		return psutil.Popen(
			[
				sys.executable,
				"-m", "flask", _CRON_COMMAND_NAME,
			],
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
		)

	process:psutil.Popen = _spawn_worker_process()

	while True:
		with process.oneshot():
			if not process.is_running():
				process = _spawn_worker_process()
				continue
			mem_rss:int = process.memory_info().rss
			if mem_rss > MAXIMUM_MEMORY_RSS:
				logging.warning("Killing and restarting cron worker with PID "
		    		f"{process.pid} due to high memory usage ({mem_rss} MB vs "
		 			f"maximum {MAXIMUM_MEMORY_RSS} MB)")
				process.terminate()
		time.sleep(CRON_SLEEP_SECONDS)


@app.cli.command(_CRON_COMMAND_NAME)
def cron_app_worker():
	'''
	The "worker" process task. This actually executes tasks.
	'''
	db:scoped_session = db_session() # type: ignore
	while True:
		try:
			_run_tasks(db)
		except Exception as e:
			logging.exception(
				"An unhandled exception occurred while running tasks",
				exc_info=e
			)
		time.sleep(CRON_SLEEP_SECONDS)


@contextlib.contextmanager
def _acquire_lock_exclusive(db:scoped_session, table:str):
	'''
	Acquires an exclusive lock on the table provided by the `table` parameter.
	This can be used for synchronizing the state of the specified table and 
	making sure no readers can access it while in the critical section.
	''' 
	# TODO: make `table` the type LiteralString once we upgrade to python 3.11
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

	with _acquire_lock_exclusive(db, RepeatableTask.__tablename__):
		tasks:list[RepeatableTask] = db.query(RepeatableTask).filter(
			RepeatableTask.enabled == True,
			RepeatableTask.frequency_day != int(DayOfWeek.NONE),
			RepeatableTask.run_state != int(ScheduledTaskState.RUNNING),
			or_(RepeatableTask.run_time_last <= now,
				RepeatableTask.run_time_last == None),
		).all()

	for task in tasks:
		with _acquire_lock_exclusive(db, RepeatableTask.__tablename__):
			trigger_time:Optional[datetime] = \
				task.next_trigger(task.run_time_last_or_created_utc)
			if not trigger_time: continue
			if now < trigger_time: continue
			task.run_time_last = now
			task.run_state_enum = ScheduledTaskState.RUNNING
		
		run:RepeatableTaskRun = task.run(db, task.run_time_last_or_created_utc)
		if run.exception:
			# TODO: collect errors somewhere other than just here and in the 
			# task run object itself (see #220).
			logging.exception(
				f"Exception running task (ID {run.task_id}, run ID {run.id})", 
				exc_info=run.exception
			)
		with _acquire_lock_exclusive(db, RepeatableTask.__tablename__):
			task.run_state_enum = ScheduledTaskState.WAITING
