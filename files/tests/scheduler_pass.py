'''
One pass of the scheduled-task worker on a given clock, for the out-of-process backend (spec/harness/backend_process.py, RDRAMA_SPEC_SCHEDULER): `python3 -m files.tests.scheduler_pass <ISO 8601 time>`. Like the worker, it does the work the pass hands to the background itself.
'''
import sys
from datetime import datetime

from files.__main__ import db_session_factory
from files.commands.cron import tasks_run_due
from files.helpers import background

if __name__ == "__main__":
	at = datetime.fromisoformat(sys.argv[1])
	tasks_run_due(db_session_factory, lambda: at)
	background.drain()
