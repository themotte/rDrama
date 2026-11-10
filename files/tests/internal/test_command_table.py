'''
The site's own command-line commands are exactly the spec's command table (spec/harness/commands.py COMMANDS), which take no arguments, and the current implementation's own below.
'''
import files.cli  # noqa: F401  (registers the migration commands)
from files.__main__ import app
from files.tests.spec.harness.commands import COMMANDS
from files.tests.testenv import REPO_ROOT

FLASKS_OWN = {"run", "shell", "routes"}

IMPLEMENTATION_ONLY = {
	"comment_counts_recalc": "a one-off repair of stored comment counts (internal/test_comment_counts_recalc.py)",
	"vote_counts_recalc": "a one-off repair of stored vote counts (internal/test_vote_counts_recalc.py)",
	"db": "Alembic's schema migrations",
	"seed_db": "a developer's tool filling a database with made-up content",
	"profile_url": "a developer's tool timing and profiling one page",
}


def test_the_site_offers_the_table_and_its_own_commands():
	assert set(app.cli.list_commands(None)) - FLASKS_OWN == COMMANDS.keys() | IMPLEMENTATION_ONLY.keys()


def test_specified_commands_take_no_arguments():
	assert {name: [p.name for p in app.cli.get_command(None, name).params] for name in COMMANDS} == {name: [] for name in COMMANDS}


def test_each_cited_spec_exists():
	assert [name for name, c in COMMANDS.items() if not (REPO_ROOT / "files" / "tests" / "spec" / c.spec).exists()] == []
