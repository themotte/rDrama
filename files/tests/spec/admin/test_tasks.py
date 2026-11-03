'''
Repeatable tasks, which the site runs on a schedule (scheduled posts are one kind; see test_scheduled_posts for the schedule fields):
- GET /tasks/<id>/ shows one task, including when it next runs.
- POST /tasks/<id>/schedule replaces its schedule.
'''
from datetime import time

from files.tests.spec.harness import *

MONDAY, TUESDAY = 1 << 2, 1 << 3


def _task(admin, *, enabled, frequency_day):
	task = db.insert("tasks_repeatable", author_id=admin["id"], type_id=1, enabled=enabled, run_state=1, frequency_day=frequency_day, time_of_day_utc="01:00", created_utc=1000)
	db.insert("tasks_repeatable_python", id=task["id"], import_path="files.helpers.config.const", callable="nothing")
	return task


def test_admin_replaces_a_tasks_schedule():
	admin = factories.admin(2)
	task = _task(admin, enabled=False, frequency_day=MONDAY)
	client = as_user(admin)

	with db_diff() as d:
		r = client.post(f"/tasks/{task['id']}/schedule", {"schedule_day_tuesday": "on", "hour": "22", "minute": "0", "enabled": "on"})

	assert_redirect(r, f"/tasks/{task['id']}")
	d.assert_exactly(updated={"tasks_repeatable": {task["id"]: {"enabled": True, "frequency_day": TUESDAY, "time_of_day_utc": time(22, 0)}}})
