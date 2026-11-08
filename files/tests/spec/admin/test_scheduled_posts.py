'''
Scheduled posts, which admins write ahead of time for the site to post on a schedule:
- GET /tasks/scheduled_posts/ lists them; GET /tasks/scheduled_posts/<id> shows one, as its posts will look.
- POST /tasks/scheduled_posts/ creates one from "title", "url" and "body" plus a schedule.
- POST /tasks/scheduled_posts/<id>/schedule replaces its schedule.
- POST /tasks/scheduled_posts/<id>/content edits its "title" and "body", under the same rules as submitting a post; an edit must change at least one of them. Redirects to the scheduled post's page.

A schedule is "hour" (0-23) and "minute" (0-59), in UTC, where anything else is refused with 400, "enabled", and one "schedule_day_<weekday>" field per day it runs (sunday through saturday); a checkbox counts as ticked when sent with a non-empty value. The days are stored in `tasks_repeatable.frequency_day` as bits: Sunday 1<<1, Monday 1<<2, through Saturday 1<<7.

Creating a schedule, and any save that changes whether it's enabled, its days or its time, records when in `tasks_repeatable.schedule_changed_utc` (UTC, without a zone); an unchanged save changes nothing. See spec/scheduler/test_schedule.py for what that does.
'''
from datetime import time

import pytest

from files.tests.spec.harness import *

MONDAY, FRIDAY, SUNDAY, SATURDAY = 1 << 2, 1 << 6, 1 << 1, 1 << 7


def _scheduled_post(admin, *, enabled=False, frequency_day=0):
	return factories.scheduled_post(admin, enabled=enabled, frequency_day=frequency_day, time_of_day_utc="01:00")


def _unknown_id():
	return db.execute("SELECT nextval('tasks_repeatable_id_seq')")


def test_admin_creates_a_scheduled_post_for_the_ticked_days():
	admin = factories.admin(2)
	title, body = factories.unique(), factories.unique()
	client = as_user(admin)

	# Creation records when the task was created, which created_utc holds to the second
	before = utc_now_naive().replace(microsecond=0)
	with db_diff() as d:
		r = client.post("/tasks/scheduled_posts/", {"title": title, "body": body, "schedule_day_monday": "on", "schedule_day_friday": "on", "hour": "13", "minute": "30", "enabled": "on"})

	task_id = d.inserted["tasks_repeatable"][0]["id"] if d.inserted.get("tasks_repeatable") else None
	assert_redirect(r, f"/tasks/scheduled_posts/{task_id}")
	d.assert_exactly(inserted={
		"tasks_repeatable": [{"id": task_id, "author_id": admin["id"], "type_id": 2, "run_state": 1, "enabled": True, "frequency_day": MONDAY | FRIDAY, "time_of_day_utc": time(13, 30), "schedule_changed_utc": between(before, utc_now_naive())}],
		"tasks_repeatable_scheduled_submissions": [{"id": task_id, "author_id_submission": admin["id"], "title": title, "body": body, "ghost": False, "private": False, "over_18": False, "is_bot": False}],
	})


@pytest.mark.parametrize("hour, minute", [("24", "0"), ("1", "60")])
def test_a_scheduled_post_outside_the_day_is_refused(hour, minute):
	admin = factories.admin(2)

	with db_diff() as d:
		r = as_user(admin).post("/tasks/scheduled_posts/", {"title": factories.unique(), "body": factories.unique(), "schedule_day_monday": "on", "hour": hour, "minute": minute}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


def test_admin_replaces_a_scheduled_posts_schedule():
	admin = factories.admin(2)
	task = _scheduled_post(admin, enabled=True, frequency_day=MONDAY)
	client = as_user(admin)

	before = utc_now_naive()
	with db_diff() as d:
		r = client.post(f"/tasks/scheduled_posts/{task['id']}/schedule", {"schedule_day_sunday": "on", "schedule_day_saturday": "on", "hour": "7", "minute": "5"})

	assert_redirect(r, f"/tasks/scheduled_posts/{task['id']}")
	d.assert_exactly(updated={"tasks_repeatable": {task["id"]: {"enabled": False, "frequency_day": SUNDAY | SATURDAY, "time_of_day_utc": time(7, 5), "schedule_changed_utc": between(before, utc_now_naive())}}})


def test_invalid_scheduled_post_edits_are_refused():
	admin = factories.admin(2)
	task = _scheduled_post(admin)
	client = as_user(admin)

	with db_diff() as d:
		r = client.post(f"/tasks/scheduled_posts/{task['id']}/content", {"title": "t", "body": ""}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


def test_scheduled_post_list_shows_every_scheduled_post():
	admin = factories.admin(2)
	scheduled = [_scheduled_post(admin), _scheduled_post(admin, enabled=True, frequency_day=MONDAY)]

	r = as_user(admin).get("/tasks/scheduled_posts/")

	assert_html(r, 200)
	for p in scheduled:
		assert_in_payload(r, p["title"])


def test_scheduled_post_page_shows_its_content():
	admin = factories.admin(2)
	scheduled = _scheduled_post(admin)

	r = as_user(admin).get(f"/tasks/scheduled_posts/{scheduled['id']}")

	assert_html(r, 200)
	assert_in_payload(r, scheduled["title"])
	assert_in_payload(r, scheduled["body"])


def test_scheduled_posts_task_page_shows_its_title():
	admin = factories.admin(2)
	scheduled = _scheduled_post(admin)

	r = as_user(admin).get(f"/tasks/{scheduled['id']}/")

	assert_html(r, 200)
	assert_in_payload(r, scheduled["title"])


def test_unknown_scheduled_posts_are_not_found():
	admin = factories.admin(2)

	assert_status(as_user(admin).get(f"/tasks/scheduled_posts/{_unknown_id()}"), 404)


def test_admin_edits_a_scheduled_posts_title_and_body():
	admin = factories.admin(2)
	scheduled = _scheduled_post(admin)
	title, body = factories.unique("title"), factories.unique("body")

	with db_diff() as d:
		r = as_user(admin).post(f"/tasks/scheduled_posts/{scheduled['id']}/content", {"title": title, "body": body})

	assert_redirect(r, f"/tasks/scheduled_posts/{scheduled['id']}")
	d.assert_exactly(updated={"tasks_repeatable_scheduled_submissions": {scheduled["id"]: {"title": title, "body": body, "body_html": ANY}}})
	assert body in db.row("tasks_repeatable_scheduled_submissions", id=scheduled["id"])["body_html"]


def test_admin_edits_only_a_scheduled_posts_title():
	admin = factories.admin(2)
	scheduled = _scheduled_post(admin)
	title = factories.unique("title")

	with db_diff() as d:
		r = as_user(admin).post(f"/tasks/scheduled_posts/{scheduled['id']}/content", {"title": title, "body": scheduled["body"]})

	assert_redirect(r, f"/tasks/scheduled_posts/{scheduled['id']}")
	d.assert_exactly(updated={"tasks_repeatable_scheduled_submissions": {scheduled["id"]: {"title": title}}})


def test_admin_edits_only_a_scheduled_posts_body():
	admin = factories.admin(2)
	scheduled = _scheduled_post(admin)
	body = factories.unique("body")

	with db_diff() as d:
		r = as_user(admin).post(f"/tasks/scheduled_posts/{scheduled['id']}/content", {"title": scheduled["title"], "body": body})

	assert_redirect(r, f"/tasks/scheduled_posts/{scheduled['id']}")
	d.assert_exactly(updated={"tasks_repeatable_scheduled_submissions": {scheduled["id"]: {"body": body, "body_html": ANY}}})


def test_a_scheduled_post_edit_that_changes_nothing_is_refused():
	admin = factories.admin(2)
	scheduled = _scheduled_post(admin)

	with db_diff() as d:
		r = as_user(admin).post(f"/tasks/scheduled_posts/{scheduled['id']}/content", {"title": scheduled["title"], "body": scheduled["body"]}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


def test_editing_an_unknown_scheduled_post_is_not_found():
	admin = factories.admin(2)

	with db_diff() as d:
		r = as_user(admin).post(f"/tasks/scheduled_posts/{_unknown_id()}/content", {"title": factories.unique("title"), "body": factories.unique("body")}, headers=XHR)

	assert_status(r, 404)
	d.assert_exactly()
