'''
The site's command-line commands a reimplementation must offer, each with the spec pinning what it does. The harness runs them by these names (cli); none takes arguments. The current implementation has others of its own (one-off repairs, schema migrations, developer tools), which aren't listed.
'''
import typing


class Command(typing.NamedTuple):
	spec: str
	'''The spec file or directory pinning what it does.'''
	note: str


COMMANDS = {
	"cron": Command("scheduler", "The scheduler: runs forever, doing a pass over the due jobs every 15 seconds. The spec runs single passes (run_scheduler)."),
	"cron_setup": Command("scheduler/test_builtin_jobs.py", "Creates the built-in scheduled jobs that are missing; run at every start."),
	"leaderboard_recalc": Command("users/test_leaderboard.py", "Recomputes the cached leaderboards, as their nightly job does; run at every start."),
	"volunteer_janitor_recalc": Command("volunteer/test_nightly_recalc.py", "Recomputes the volunteer janitor estimates, as their nightly job does."),
}
