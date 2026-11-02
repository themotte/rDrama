'''
Points the app at an isolated database, Redis db and site-settings file, and builds that database from scratch.

`files.__main__` creates its engine, cache and limiter at import time, so `configure()` must run before anything imports it. Set RDRAMA_TEST_DB / RDRAMA_TEST_REDIS_DB to run several suites against the same servers at once.
'''
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg2
from sqlalchemy.engine import make_url

TEST_DB_NAME = os.environ.get("RDRAMA_TEST_DB", "rdrama_test")
TEST_REDIS_DB = int(os.environ.get("RDRAMA_TEST_REDIS_DB", "1"))
SNAPSHOT_SCHEMA = "test_seed_snapshot"

REPO_ROOT = Path(__file__).resolve().parents[2]

_baseline_settings: str | None = None


def configure():
	global _baseline_settings
	server_url = make_url(os.environ["DATABASE_URL"])
	test_url = server_url.set(database=TEST_DB_NAME)

	os.environ["DATABASE_URL"] = test_url.render_as_string(hide_password=False)
	os.environ["REDIS_URL"] = urlunsplit(urlsplit(os.environ["REDIS_URL"])._replace(path=f"/{TEST_REDIS_DB}"))
	scratch = Path(tempfile.mkdtemp(prefix="rdrama-test-"))
	os.environ["SITE_SETTINGS_PATH"] = str(scratch / "site_settings.json")
	os.environ["IMAGES_DIR"] = str(scratch / "images")
	(scratch / "images").mkdir()
	os.environ["RDRAMA_SERVICE"] = "THEMOTTE"
	os.environ["RDRAMA_TESTING"] = "1"
	os.environ["DBG_LIMITER_DISABLED"] = "true"

	# The committed defaults, not the working copy, which a local dev server's admin toggles rewrite
	_baseline_settings = subprocess.run(["git", "-c", "safe.directory=*", "show", "HEAD:site_settings.json"], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout
	restore_site_settings()
	_build_database(server_url, test_url)


def restore_site_settings():
	Path(os.environ["SITE_SETTINGS_PATH"]).write_text(_baseline_settings)


def _dsn(url):
	return url.render_as_string(hide_password=False)


def _build_database(server_url, test_url):
	admin = psycopg2.connect(_dsn(server_url.set(database="postgres")))
	admin.autocommit = True
	with admin.cursor() as cur:
		cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME} WITH (FORCE)")
		cur.execute(f"CREATE DATABASE {TEST_DB_NAME}")
	admin.close()

	conn = psycopg2.connect(_dsn(test_url))
	with conn, conn.cursor() as cur:
		for name in ("original-schema.sql", "original-seed-db.sql"):
			cur.execute((REPO_ROOT / "bootstrap" / name).read_text())
	conn.close()

	# alembic's env.py calls logging.fileConfig, which disables existing loggers; keep it out of the test process
	result = subprocess.run(
		["python3", "-m", "flask", "db", "upgrade"],
		cwd=REPO_ROOT,
		env={**os.environ, "RDRAMA_SERVICE": "MIGRATION"},
		capture_output=True,
		text=True,
	)
	if result.returncode != 0:
		raise RuntimeError(f"Test database migration failed:\n{result.stdout}\n{result.stderr}")

	_snapshot_seed_rows(test_url)


def _snapshot_seed_rows(test_url):
	'''Copies every non-empty table (seed users, badge definitions, rows inserted by migrations) so `reset` can restore them.'''
	conn = psycopg2.connect(_dsn(test_url))
	with conn, conn.cursor() as cur:
		cur.execute(f"CREATE SCHEMA {SNAPSHOT_SCHEMA}")
		cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename != 'alembic_version' ORDER BY tablename")
		for (table,) in cur.fetchall():
			cur.execute(f'SELECT EXISTS (SELECT 1 FROM public."{table}")')
			if cur.fetchone()[0]:
				cur.execute(f'CREATE TABLE {SNAPSHOT_SCHEMA}."{table}" AS TABLE public."{table}"')
	conn.close()
