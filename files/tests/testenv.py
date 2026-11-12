'''
Points the app at an isolated database, Redis db and site-settings file, builds that database from scratch, and drops it again.

`files.__main__` creates its engine, cache and limiter at import time, so `configure()` must run before anything imports it; `build_database()` may come later, before the first test.

Set RDRAMA_TEST_DB / RDRAMA_TEST_REDIS_DB to run several suites against the same servers at once. Under pytest-xdist each worker gwN takes database `<RDRAMA_TEST_DB>_gwN` and Redis db `<RDRAMA_TEST_REDIS_DB> + 1 + N`, so concurrent parallel suites need Redis bases at least their worker count apart (the compose Redis has 64 dbs).
'''
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg2
from sqlalchemy.engine import make_url

WORKER = os.environ.get("PYTEST_XDIST_WORKER")  # "gw0", "gw1", ... in an xdist worker
TEST_DB_NAME = os.environ.get("RDRAMA_TEST_DB", "rdrama_test") + (f"_{WORKER}" if WORKER else "")
TEST_REDIS_DB = int(os.environ.get("RDRAMA_TEST_REDIS_DB", "1")) + (1 + int(WORKER.removeprefix("gw")) if WORKER else 0)

REPO_ROOT = Path(__file__).resolve().parents[2]

def configure():
	server_url = make_url(os.environ["DATABASE_URL"])
	test_url = server_url.set(database=TEST_DB_NAME)

	os.environ["DATABASE_URL"] = test_url.render_as_string(hide_password=False)
	os.environ["REDIS_URL"] = urlunsplit(urlsplit(os.environ["REDIS_URL"])._replace(path=f"/{TEST_REDIS_DB}"))
	scratch = Path(tempfile.mkdtemp(prefix="rdrama-test-"))
	os.environ["SITE_SETTINGS_PATH"] = str(scratch / "site_settings.json")
	os.environ["IMAGES_DIR"] = str(scratch / "images")
	(scratch / "images").mkdir()
	os.environ["RDRAMA_SERVICE"] = "THEMOTTE"
	os.environ["SPEC_TEST_MODE"] = "1"

	# Imported once the environment points at the test database, since importing the harness may import the app
	from files.tests.spec.harness import state
	state.write_site_settings()


def build_database():
	from files.tests.spec.harness import state
	_build_database(make_url(os.environ["DATABASE_URL"]))
	state.snapshot()


def drop_database():
	'''Drops the database `build_database` built: the next run builds its own, and the server then needn't flush this run's unflushed pages, which can hold up its shutdown for minutes.'''
	_server_execute(make_url(os.environ["DATABASE_URL"]), f"DROP DATABASE IF EXISTS {TEST_DB_NAME} WITH (FORCE)")


def _dsn(url):
	return url.render_as_string(hide_password=False)


def _server_execute(test_url, *statements):
	'''Runs statements that act on whole databases, from the server's maintenance database.'''
	admin = psycopg2.connect(_dsn(test_url.set(database="postgres")))
	admin.autocommit = True
	with admin.cursor() as cur:
		for statement in statements:
			cur.execute(statement)
	admin.close()


def _build_database(test_url):
	_server_execute(test_url, f"DROP DATABASE IF EXISTS {TEST_DB_NAME} WITH (FORCE)", f"CREATE DATABASE {TEST_DB_NAME}")

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

