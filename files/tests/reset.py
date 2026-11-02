'''
Returns the app's external state (database, Redis, site settings) to the freshly-built baseline.

Purely external: it truncates tables and restores the seed snapshot rather than wrapping the app in a transaction, so it works the same against any implementation running on this schema. The caller must first make the app release any open transactions. Sequences are deliberately not restarted: ids are never reused, so a stale session cookie can't silently resolve to a different user.
'''
import os

import redis
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from files.tests import testenv

_engine = None
_tables: list[str] | None = None
_snapshot_tables: list[str] | None = None


def reset():
	global _engine
	if _engine is None:
		_engine = create_engine(os.environ["DATABASE_URL"])
	with _engine.connect() as conn:
		_load_table_lists(conn)
		conn.execute(text("SET lock_timeout = '5s'"))
		try:
			conn.execute(text("TRUNCATE " + ", ".join(f'public."{t}"' for t in _tables) + " CASCADE"))
		except OperationalError as e:
			conn.rollback()
			raise RuntimeError(f"Reset could not lock the tables; open sessions:\n{_describe_sessions(conn)}") from e
		# Restore in one pass without FK ordering; the snapshot was consistent when taken
		conn.execute(text("SET LOCAL session_replication_role = replica"))
		for table in _snapshot_tables:
			conn.execute(text(f'INSERT INTO public."{table}" SELECT * FROM {testenv.SNAPSHOT_SCHEMA}."{table}"'))
		conn.commit()

	redis.Redis.from_url(os.environ["REDIS_URL"]).flushdb()
	testenv.restore_site_settings()


def _describe_sessions(conn):
	rows = conn.execute(text("SELECT pid, state, xact_start, left(query, 200) FROM pg_stat_activity WHERE datname = current_database() AND pid != pg_backend_pid()")).all()
	return "\n".join(f"  pid={pid} state={state} xact_start={xact_start} query={query!r}" for pid, state, xact_start, query in rows)


def _load_table_lists(conn):
	global _tables, _snapshot_tables
	if _tables is not None:
		return
	_tables = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename != 'alembic_version' ORDER BY tablename")).scalars().all()
	_snapshot_tables = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = :schema ORDER BY tablename"), {"schema": testenv.SNAPSHOT_SCHEMA}).scalars().all()
