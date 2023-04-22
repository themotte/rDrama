
from typing import Optional
import datetime

import sqlalchemy
from sqlalchemy.orm import Session

from files.__main__ import app, db_session
from files.classes.cron.pycallable import PythonCodeTask
from files.classes.cron.tasks import DayOfWeek
from files.helpers.config.const import AUTOJANNY_ID


@app.cli.command('cron_setup')
def cron_setup():
    db: Session = db_session()

    tasklist = db.query(PythonCodeTask)

    # I guess in theory we should load this from a file or something, but, ehhhh
    hardcoded_cron_jobs = {
        #'testjob': {
            #'frequency_day': DayOfWeek.ALL,
            #'time_of_day_utc': datetime.time(0, 0),
            #'import_path': 'files.commands.debug_printout',
            #'callable': 'printstuff',
        #},
    }

    print(f"{tasklist.count()} tasks")
    for task in tasklist:
        if task.label and task.label in hardcoded_cron_jobs:
            print(f"Cron: Updating {task.label}")
            ref = hardcoded_cron_jobs[task.label]
            task.frequency_day = ref["frequency_day"]
            task.time_of_day_utc = ref["time_of_day_utc"]
            task.import_path = ref["import_path"]
            task.callable = ref["callable"]
            del hardcoded_cron_jobs[task.label]
    
    for label, ref in hardcoded_cron_jobs.items():
        print(f"Cron: Creating {label}")
        task: PythonCodeTask = PythonCodeTask(
            label = label,
            author_id = AUTOJANNY_ID,
            frequency_day = ref["frequency_day"],
            time_of_day_utc = ref["time_of_day_utc"],
            import_path = ref["import_path"],
            callable = ref["callable"],
        )
        db.add(task)

    db.commit()
