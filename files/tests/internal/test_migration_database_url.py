'''
Migrations run against the configured DATABASE_URL whatever its password holds: a password with characters a URL must percent-escape (here "@", written "%40") reaches the database as written. The compose Postgres trusts any password, so this checks that the URL is taken as given, not that the password is checked.
'''
import os
import subprocess

from sqlalchemy.engine import make_url

from files.tests.testenv import REPO_ROOT


def test_a_password_with_escaped_characters_migrates():
	url = make_url(os.environ["DATABASE_URL"]).set(password="p@ss").render_as_string(hide_password=False)
	assert "p%40ss" in url

	result = subprocess.run(["python3", "-m", "flask", "db", "current"], cwd=REPO_ROOT, env={**os.environ, "DATABASE_URL": url, "RDRAMA_SERVICE": "MIGRATION"}, capture_output=True, text=True)

	assert result.returncode == 0, result.stderr
	assert "(head)" in result.stdout, result.stdout + result.stderr
