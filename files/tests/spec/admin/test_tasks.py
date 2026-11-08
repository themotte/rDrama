'''
Repeatable tasks, which the site runs on a schedule (scheduled posts are one kind; see test_scheduled_posts for the schedule fields):
- GET /tasks/ lists every task, linking to each one's page.
- GET /tasks/<id>/ shows one task, including when it next runs, what it runs, and links to its runs. /tasks/<id>/runs/ redirects there.
- GET /tasks/<id>/runs/<run_id> shows one run; the traceback of a failed run is shown only to admins of level 3 and up. A run asked for under another task's id redirects to its own task's URL.
- POST /tasks/<id>/schedule replaces its schedule.
'''
import re
from datetime import time

import pytest

from files.tests.spec.harness import *

MONDAY, TUESDAY = 1 << 2, 1 << 3


def _task(admin, *, enabled=True, frequency_day=MONDAY):
	return factories.job(admin, "files.helpers.config.const", factories.unique("callable"), enabled=enabled, frequency_day=frequency_day, time_of_day_utc="01:00")


def _links(r) -> set[str]:
	return set(re.findall(r'href="([^"]*)"', r.text))


def test_admin_replaces_a_tasks_schedule():
	admin = factories.admin(2)
	task = _task(admin, enabled=False, frequency_day=MONDAY)
	client = as_user(admin)

	before = utc_now_naive()
	with db_diff() as d:
		r = client.post(f"/tasks/{task['id']}/schedule", {"schedule_day_tuesday": "on", "hour": "22", "minute": "0", "enabled": "on"})

	assert_redirect(r, f"/tasks/{task['id']}")
	d.assert_exactly(updated={"tasks_repeatable": {task["id"]: {"enabled": True, "frequency_day": TUESDAY, "time_of_day_utc": time(22, 0), "schedule_changed_utc": between(before, utc_now_naive())}}})


@pytest.mark.parametrize("change, changed", [
	({"enabled": "on"}, {"enabled": True}),
	({"schedule_day_tuesday": "on"}, {"frequency_day": MONDAY | TUESDAY}),
	({"hour": "2"}, {"time_of_day_utc": time(2, 0)}),
], ids=["enabled", "days", "time"])
def test_any_schedule_change_records_when_it_was_made(change, changed):
	admin = factories.admin(2)
	task = _task(admin, enabled=False, frequency_day=MONDAY)
	client = as_user(admin)

	before = utc_now_naive()
	with db_diff() as d:
		r = client.post(f"/tasks/{task['id']}/schedule", {"schedule_day_monday": "on", "hour": "1", "minute": "0", **change})

	assert_redirect(r, f"/tasks/{task['id']}")
	d.assert_exactly(updated={"tasks_repeatable": {task["id"]: {**changed, "schedule_changed_utc": between(before, utc_now_naive())}}})


def test_saving_an_unchanged_schedule_changes_nothing():
	admin = factories.admin(2)
	task = _task(admin, enabled=True, frequency_day=MONDAY)

	with db_diff() as d:
		r = as_user(admin).post(f"/tasks/{task['id']}/schedule", {"schedule_day_monday": "on", "hour": "1", "minute": "0", "enabled": "on"})

	assert_redirect(r, f"/tasks/{task['id']}")
	d.assert_exactly()


def test_an_enabled_task_with_no_days_ticked_has_a_page():
	admin = factories.admin(2)
	task = _task(admin, enabled=True, frequency_day=0)

	r = as_user(admin).get(f"/tasks/{task['id']}/")

	assert_status(r, 200)


def test_task_list_links_every_task():
	admin = factories.admin(2)
	tasks = [_task(admin), _task(admin, enabled=False)]

	r = as_user(admin).get("/tasks/")

	assert_html(r, 200)
	assert {f"/tasks/{t['id']}" for t in tasks} <= _links(r)


def test_task_page_shows_what_it_runs_and_links_its_runs():
	admin = factories.admin(2)
	task = _task(admin)
	run = factories.task_run(task)

	r = as_user(admin).get(f"/tasks/{task['id']}/")

	assert_html(r, 200)
	assert_in_payload(r, task["callable"])
	assert f"/tasks/{task['id']}/runs/{run['id']}" in _links(r)


def test_unknown_tasks_are_not_found():
	admin = factories.admin(2)
	unknown = db.execute("SELECT nextval('tasks_repeatable_id_seq')")

	assert_status(as_user(admin).get(f"/tasks/{unknown}/"), 404)


def test_task_runs_index_redirects_to_the_task():
	admin = factories.admin(2)
	task = _task(admin)

	assert_redirect(as_user(admin).get(f"/tasks/{task['id']}/runs/"), f"/tasks/{task['id']}/")


@pytest.mark.parametrize("level, shown", [(2, False), (3, True)])
def test_run_page_shows_a_failed_runs_traceback_only_to_head_admins(level, shown):
	admin = factories.admin(level)
	traceback = factories.unique("traceback")
	run = factories.task_run(_task(admin), traceback_str=traceback)

	r = as_user(admin).get(f"/tasks/{run['task_id']}/runs/{run['id']}")

	assert_html(r, 200)
	(assert_in_payload if shown else assert_not_in_payload)(r, traceback)


def test_run_asked_for_under_another_task_redirects_to_its_own():
	admin = factories.admin(2)
	task, other = _task(admin), _task(admin)
	run = factories.task_run(task)

	r = as_user(admin).get(f"/tasks/{other['id']}/runs/{run['id']}")

	assert_redirect(r, f"/tasks/{task['id']}/runs/{run['id']}")


def test_unknown_runs_are_not_found():
	admin = factories.admin(2)
	task = _task(admin)

	unknown = db.execute("SELECT nextval('tasks_repeatable_runs_id_seq')")

	assert_status(as_user(admin).get(f"/tasks/{task['id']}/runs/{unknown}"), 404)
