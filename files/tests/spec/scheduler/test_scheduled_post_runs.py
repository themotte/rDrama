'''
What the scheduled-task worker makes when a scheduled post (see spec/admin/test_scheduled_posts.py) runs: a new post, made at the run's time.
'''
import calendar
from datetime import datetime, timezone

from files.tests.spec.harness import *

MONDAY = 1 << 2
SLOT = datetime(2024, 1, 8, 8, 0, tzinfo=timezone.utc)
'''A Monday 08:00 UTC.'''
CREATED = calendar.timegm((2024, 1, 1, 0, 0, 0))


def test_a_due_scheduled_post_makes_a_post():
	admin = factories.admin(2)
	scheduled = factories.scheduled_post(admin, frequency_day=MONDAY, time_of_day_utc="08:00", created_utc=CREATED)

	run_scheduler(SLOT)

	assert [p["title"] for p in db.rows("submissions", task_id=scheduled["id"])] == [scheduled["title"]]
	assert db.row("tasks_repeatable", id=scheduled["id"])["run_state"] == 1
