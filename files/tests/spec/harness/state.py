'''
The state the site shares with the harness (the database, the Redis db, the site settings file and the upload store), and putting it back between tests: every test starts from the database as the runner built it, an empty Redis db, the default site settings and no uploads.

Purely external, so it works the same against any implementation running on this schema. The site must hold no open transaction between requests, since the reset's truncate waits for its locks only a few seconds.
'''
import json
import os
import shutil
from pathlib import Path

import redis
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from files.tests.spec.harness import config

SNAPSHOT_SCHEMA = "test_seed_snapshot"
'''Where the database's rows as built are kept, for restoring them.'''

_engine = None
_tables: list[str] | None = None
_snapshot_tables: list[str] | None = None


def write_site_settings():
	Path(config.site_settings_path()).write_text(json.dumps({name: setting.default for name, setting in config.SITE_SETTINGS.items()}))


def snapshot():
	'''Keeps the rows the database holds, to restore before every test: done once per process, on the database as the runner built it for this process, before the site first runs.'''
	global _tables, _snapshot_tables
	if _snapshot_tables is not None:
		return
	with _connection() as conn:
		if conn.execute(text("SELECT 1 FROM pg_namespace WHERE nspname = :schema"), {"schema": SNAPSHOT_SCHEMA}).first():
			raise RuntimeError(f"the database already holds a snapshot ({SNAPSHOT_SCHEMA}): the spec runs on a database built fresh for the run")
		conn.execute(text(f"CREATE SCHEMA {SNAPSHOT_SCHEMA}"))
		for table in _public_tables(conn):
			if conn.execute(text(f'SELECT EXISTS (SELECT 1 FROM public."{table}")')).scalar():
				conn.execute(text(f'CREATE TABLE {SNAPSHOT_SCHEMA}."{table}" AS TABLE public."{table}"'))
		conn.commit()
		_tables = _public_tables(conn)
		_snapshot_tables = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = :schema ORDER BY tablename"), {"schema": SNAPSHOT_SCHEMA}).scalars().all()


def reset():
	'''Puts the shared state back. The rows' ids keep counting up: sequences aren't rewound, so no id is reused within a run.'''
	snapshot()
	with _connection() as conn:
		conn.execute(text("SET lock_timeout = '5s'"))
		try:
			conn.execute(text("TRUNCATE " + ", ".join(f'public."{t}"' for t in _tables) + " CASCADE"))
		except OperationalError as e:
			conn.rollback()
			raise RuntimeError(f"Reset could not lock the tables; open sessions:\n{_describe_sessions(conn)}") from e
		# Restore in one pass without FK ordering; the snapshot was consistent when taken
		conn.execute(text("SET LOCAL session_replication_role = replica"))
		for table in _snapshot_tables:
			conn.execute(text(f'INSERT INTO public."{table}" SELECT * FROM {SNAPSHOT_SCHEMA}."{table}"'))
		conn.commit()

	redis.Redis.from_url(os.environ["REDIS_URL"]).flushdb()
	write_site_settings()
	images = Path(config.images_dir())
	shutil.rmtree(images)
	images.mkdir()


def _connection():
	global _engine
	if _engine is None:
		_engine = create_engine(os.environ["DATABASE_URL"])
	return _engine.connect()


def _public_tables(conn) -> list[str]:
	'''The site's tables, but not the schema version marker, which belongs to the current schema's tooling.'''
	return conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename != 'alembic_version' ORDER BY tablename")).scalars().all()


def _describe_sessions(conn):
	rows = conn.execute(text("SELECT pid, state, xact_start, left(query, 200) FROM pg_stat_activity WHERE datname = current_database() AND pid != pg_backend_pid()")).all()
	return "\n".join(f"  pid={pid} state={state} xact_start={xact_start} query={query!r}" for pid, state, xact_start, query in rows)
