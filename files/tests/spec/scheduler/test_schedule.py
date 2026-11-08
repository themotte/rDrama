'''
When the scheduled-task worker runs a task.
'''
import calendar
from datetime import datetime, timedelta, timezone

from files.tests.spec.harness import *

MONDAY = 1 << 2
SLOT = datetime(2024, 1, 8, 8, 0, tzinfo=timezone.utc)
'''A Monday 08:00 UTC.'''
CREATED = calendar.timegm((2024, 1, 1, 0, 0, 0))


def _posts(scheduled) -> int:
	return len(db.rows("submissions", task_id=scheduled["id"]))


def test_a_task_runs_once_per_slot_even_when_passes_fall_exactly_on_it():
	scheduled = factories.scheduled_post(factories.admin(2), frequency_day=MONDAY, time_of_day_utc="08:00", created_utc=CREATED)

	run_scheduler(SLOT)
	run_scheduler(SLOT)
	run_scheduler(SLOT + timedelta(minutes=1))

	assert _posts(scheduled) == 1
