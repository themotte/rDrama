import os
import subprocess

from files.tests import testenv


def test_migrations_up_to_date():
	'''The models match the schema the migrations build: `flask db check` finds nothing for a new migration to do.'''
	result = subprocess.run(
		["python3", "-m", "flask", "db", "check"],
		cwd=testenv.REPO_ROOT,
		env={**os.environ, "FLASK_APP": "files/cli:app", "RDRAMA_SERVICE": "MIGRATION"},
		capture_output=True,
		text=True,
	)
	assert result.returncode == 0, "\n".join([
		"The models and the migrations differ. Run",
		"\t$ flask db revision --autogenerate --message='short description of schema changes'",
		"to generate a candidate migration, and make any necessary changes to that candidate migration (e.g. naming foreign key constraints).",
		result.stdout,
		result.stderr,
	])
