'''
When the scheduled-task worker (the `cron` command; exactly one runs) runs a task. It looks over the tasks every few seconds.

A task's schedule (`tasks_repeatable`, set as spec/admin/test_scheduled_posts.py describes) gives its slots: each ticked weekday (`frequency_day`) at `time_of_day_utc`, in UTC. A task is due once the first slot strictly after its anchor has come: the later of its last run (`run_time_last`) and its last schedule change (`schedule_changed_utc`, which creation sets). So a task that missed slots while the worker was down runs once, not once per missed slot, while slots that passed before its schedule changed (it was enabled, or got new days or a new time) never run. A disabled task, or one with no days ticked, never runs.

Running a task sets `run_time_last` to when the run started.
'''
import calendar
from datetime import datetime, timedelta, timezone

import pytest

from files.tests.spec.harness import *

MONDAY, THURSDAY = 1 << 2, 1 << 5
EVERY_DAY = 0b11111110
SLOT = datetime(2024, 1, 8, 8, 0, tzinfo=timezone.utc)
'''A Monday 08:00 UTC.'''
CREATED = calendar.timegm((2024, 1, 2, 0, 0, 0))
'''A Tuesday, after the Monday slot before SLOT.'''


def _posts(scheduled) -> int:
	return len(db.rows("submissions", task_id=scheduled["id"]))


def _scheduled(**overrides):
	return factories.scheduled_post(factories.admin(2), **{"frequency_day": MONDAY, "time_of_day_utc": "08:00", "created_utc": CREATED, **overrides})


def test_a_task_runs_at_its_slot_and_not_before():
	scheduled = _scheduled()

	run_scheduler(SLOT - timedelta(seconds=1))
	before = _posts(scheduled)
	run_scheduler(SLOT)

	assert (before, _posts(scheduled)) == (0, 1)
	assert db.row("tasks_repeatable", id=scheduled["id"])["run_time_last"] == SLOT.replace(tzinfo=None)


def test_a_task_runs_only_on_its_ticked_weekdays():
	# Created on a Monday after its slot, so its first slot is that Thursday's
	scheduled = _scheduled(frequency_day=MONDAY | THURSDAY, created_utc=calendar.timegm((SLOT + timedelta(hours=1)).utctimetuple()))
	tuesday, wednesday, thursday = (SLOT + timedelta(days=n) for n in (1, 2, 3))

	counts = []
	for at in (SLOT + timedelta(hours=2), tuesday, wednesday, thursday - timedelta(minutes=1), thursday):
		run_scheduler(at)
		counts.append(_posts(scheduled))

	assert counts == [0, 0, 0, 0, 1]


def test_creation_counts_as_a_schedule_change():
	scheduled = _scheduled(frequency_day=EVERY_DAY, created_utc=calendar.timegm((SLOT + timedelta(minutes=1)).utctimetuple()))

	run_scheduler(SLOT + timedelta(hours=1))
	same_day = _posts(scheduled)
	run_scheduler(SLOT + timedelta(days=1))

	assert (same_day, _posts(scheduled)) == (0, 1)


@pytest.mark.parametrize("schedule", [{"enabled": False}, {"frequency_day": 0}], ids=["disabled", "no days"])
def test_a_task_without_a_live_schedule_never_runs(schedule):
	scheduled = _scheduled(**schedule)

	run_scheduler(SLOT + timedelta(days=30))

	assert _posts(scheduled) == 0


def test_a_task_that_missed_slots_runs_once():
	scheduled = _scheduled(run_time_last=datetime(2024, 1, 1, 8, 0, 5))

	run_scheduler(SLOT + timedelta(days=17))
	run_scheduler(SLOT + timedelta(days=17, minutes=1))

	assert _posts(scheduled) == 1


def test_a_task_runs_once_per_slot_even_when_passes_fall_exactly_on_it():
	scheduled = _scheduled()

	run_scheduler(SLOT)
	run_scheduler(SLOT)
	run_scheduler(SLOT + timedelta(minutes=1))

	assert _posts(scheduled) == 1


def test_after_a_schedule_change_only_later_slots_run():
	# Last ran the week before; re-enabled the day after the slot it missed
	scheduled = _scheduled(run_time_last=datetime(2024, 1, 1, 8, 0, 5), schedule_changed_utc=datetime(2024, 1, 9, 12, 0))

	run_scheduler(datetime(2024, 1, 9, 12, 1, tzinfo=timezone.utc))
	missed = _posts(scheduled)
	run_scheduler(SLOT + timedelta(days=7))

	assert (missed, _posts(scheduled)) == (0, 1)


def test_enabling_a_task_on_the_admin_page_skips_the_slots_it_missed():
	admin = factories.admin(2)
	now = datetime.now(timezone.utc)
	# Last ran over a week ago, on a schedule of every day at a time an hour past
	slot = (now - timedelta(hours=1)).replace(second=0, microsecond=0)
	scheduled = _scheduled(enabled=False, frequency_day=EVERY_DAY, time_of_day_utc=slot.time(), run_time_last=(slot - timedelta(days=8)).replace(tzinfo=None))

	assert_redirect(as_user(admin).post(f"/tasks/{scheduled['id']}/schedule", {**{f"schedule_day_{day}": "on" for day in ("sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday")}, "hour": str(slot.hour), "minute": str(slot.minute), "enabled": "on"}), f"/tasks/{scheduled['id']}")
	run_scheduler(now + timedelta(minutes=1))
	at_once = _posts(scheduled)
	run_scheduler(slot + timedelta(days=1))

	assert (at_once, _posts(scheduled)) == (0, 1)
