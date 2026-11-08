'''
The site's built-in jobs, which the `cron_setup` command (run at every deploy) puts in place as job tasks labelled by `tasks_repeatable.label`, authored by the system account 2:
- "volunteer_janitor_recalc": every day at 00:00 UTC, import_path "files.commands.volunteer_janitor_recalc", callable "volunteer_janitor_recalc_cron";
- "leaderboard_recalc": every day at 08:00 UTC, import_path "files.commands.leaderboard_recalc", callable "leaderboard_recalc_cron".

`cron_setup` creates a built-in job that's missing, enabled, with that schedule. For one that exists it only sets what it runs (import_path and callable); its schedule and whether it's enabled are the admins' (see spec/admin/test_tasks.py).
'''
from datetime import time

from files.tests.spec.harness import *

EVERY_DAY = 0b11111110
MONDAY = 1 << 2
SYSTEM = {"id": 2}
BUILTINS = {
	"volunteer_janitor_recalc": dict(time_of_day_utc=time(0, 0), import_path="files.commands.volunteer_janitor_recalc", callable="volunteer_janitor_recalc_cron"),
	"leaderboard_recalc": dict(time_of_day_utc=time(8, 0), import_path="files.commands.leaderboard_recalc", callable="leaderboard_recalc_cron"),
}


def _created(label):
	spec = BUILTINS[label]
	return [
		{"label": label, "author_id": 2, "type_id": 1, "enabled": True, "run_state": 1, "run_time_last": None, "frequency_day": EVERY_DAY, "time_of_day_utc": spec["time_of_day_utc"]},
		{"import_path": spec["import_path"], "callable": spec["callable"]},
	]


def test_setup_creates_the_builtin_jobs():
	with db_diff() as d:
		assert_cli_ok(cli("cron_setup"))

	tasks, code = zip(*(_created(label) for label in BUILTINS))
	d.assert_exactly(inserted={"tasks_repeatable": list(tasks), "tasks_repeatable_python": list(code)})


def test_setup_again_changes_nothing():
	assert_cli_ok(cli("cron_setup"))

	with db_diff() as d:
		assert_cli_ok(cli("cron_setup"))

	d.assert_exactly()


def test_setup_keeps_what_a_builtin_job_runs_but_leaves_its_schedule_to_admins():
	existing = factories.job(SYSTEM, "files.commands.old_leaderboards", "old_callable", label="leaderboard_recalc", enabled=False, frequency_day=MONDAY, time_of_day_utc="03:00")

	with db_diff() as d:
		assert_cli_ok(cli("cron_setup"))

	task, code = _created("volunteer_janitor_recalc")
	d.assert_exactly(
		inserted={"tasks_repeatable": [task], "tasks_repeatable_python": [code]},
		updated={"tasks_repeatable_python": {existing["id"]: {"import_path": BUILTINS["leaderboard_recalc"]["import_path"], "callable": BUILTINS["leaderboard_recalc"]["callable"]}}},
	)
