'''
Scheduled posts, which admins write ahead of time for the site to post on a schedule:
- POST /tasks/scheduled_posts/ creates one from "title", "url" and "body" plus a schedule.
- POST /tasks/scheduled_posts/<id>/schedule replaces its schedule.
- POST /tasks/scheduled_posts/<id>/content edits its "title" and "body", under the same rules as submitting a post.

A schedule is "hour" and "minute" (UTC), "enabled", and one "schedule_day_<weekday>" field per day it runs (sunday through saturday); a checkbox counts as ticked when sent with a non-empty value. The days are stored in `tasks_repeatable.frequency_day` as bits: Sunday 1<<1, Monday 1<<2, through Saturday 1<<7.
'''
from datetime import time

from files.tests.spec.harness import *

MONDAY, FRIDAY, SUNDAY, SATURDAY = 1 << 2, 1 << 6, 1 << 1, 1 << 7


def _scheduled_post(admin, *, enabled=False, frequency_day=0):
	task = db.insert("tasks_repeatable", author_id=admin["id"], type_id=2, enabled=enabled, run_state=1, frequency_day=frequency_day, time_of_day_utc="01:00", created_utc=1000)
	db.insert("tasks_repeatable_scheduled_submissions", id=task["id"], author_id_submission=admin["id"], ghost=False, private=False, over_18=False, is_bot=False, title="t", body="text", body_html="<p>text</p>")
	return task


def test_admin_creates_a_scheduled_post_for_the_ticked_days():
	admin = factories.admin(2)
	title, body = factories.unique(), factories.unique()
	client = as_user(admin)

	with db_diff() as d:
		r = client.post("/tasks/scheduled_posts/", {"title": title, "body": body, "schedule_day_monday": "on", "schedule_day_friday": "on", "hour": "13", "minute": "30", "enabled": "on"})

	task_id = d.inserted["tasks_repeatable"][0]["id"] if d.inserted.get("tasks_repeatable") else None
	assert_redirect(r, f"/tasks/scheduled_posts/{task_id}")
	d.assert_exactly(inserted={
		"tasks_repeatable": [{"id": task_id, "author_id": admin["id"], "type_id": 2, "run_state": 1, "enabled": True, "frequency_day": MONDAY | FRIDAY, "time_of_day_utc": time(13, 30)}],
		"tasks_repeatable_scheduled_submissions": [{"id": task_id, "author_id_submission": admin["id"], "title": title, "body": body, "ghost": False, "private": False, "over_18": False}],
	})


def test_admin_replaces_a_scheduled_posts_schedule():
	admin = factories.admin(2)
	task = _scheduled_post(admin, enabled=True, frequency_day=MONDAY)
	client = as_user(admin)

	with db_diff() as d:
		r = client.post(f"/tasks/scheduled_posts/{task['id']}/schedule", {"schedule_day_sunday": "on", "schedule_day_saturday": "on", "hour": "7", "minute": "5"})

	assert_redirect(r, f"/tasks/scheduled_posts/{task['id']}")
	d.assert_exactly(updated={"tasks_repeatable": {task["id"]: {"enabled": False, "frequency_day": SUNDAY | SATURDAY, "time_of_day_utc": time(7, 5)}}})


def test_invalid_scheduled_post_edits_are_refused():
	admin = factories.admin(2)
	task = _scheduled_post(admin)
	client = as_user(admin)

	with db_diff() as d:
		r = client.post(f"/tasks/scheduled_posts/{task['id']}/content", {"title": "t", "body": ""}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()
