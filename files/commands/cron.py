import logging
import time
from datetime import datetime, timezone
from typing import Final

from sqlalchemy.orm import scoped_session

from files.classes.cron.scheduler import RepeatableTask, RepeatableTaskRun
from files.__main__ import app, db_session

CRON_SLEEP: Final[int] = 30
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

def _run_tasks(db:scoped_session):
	tasks:list[RepeatableTask] = db.query(RepeatableTask).filter(
		RepeatableTask.enabled == True).all()
	now:datetime = datetime.now(tz=timezone.utc)
	for task in tasks:
		trigger_time:datetime | None = \
			task.next_trigger(task.last_run_or_created_utc)
		if not trigger_time: continue
		if now < trigger_time: continue
		
		run:RepeatableTaskRun = task.run(db, task.last_run_or_created_utc)
		if run.exception:
			logging.exception(
				f"Exception running task (ID {run.task_id}, run ID {run.id})", 
				exc_info=run.exception
			)
	db.commit()