'''
Direct database access at the schema level: reflected tables and plain-dict rows, never the application's models. The schema is contract, so specs may arrange and inspect rows freely.
'''
import os
from contextlib import contextmanager
from dataclasses import dataclass, field

from sqlalchemy import MetaData, Table, create_engine, select

_engine = None
_metadata: MetaData | None = None


def engine():
	global _engine
	if _engine is None:
		_engine = create_engine(os.environ["DATABASE_URL"])
	return _engine


def _reflected() -> MetaData:
	global _metadata
	if _metadata is None:
		_metadata = MetaData()
		_metadata.reflect(bind=engine(), schema="public")
	return _metadata


def table(name) -> Table:
	return _reflected().tables[f"public.{name}"]


def _where(t: Table, where: dict):
	return [t.c[k] == v for k, v in where.items()]


def rows(table_name, **where) -> list[dict]:
	t = table(table_name)
	with engine().connect() as conn:
		return [dict(r._mapping) for r in conn.execute(select(t).where(*_where(t, where)).order_by(*(t.primary_key.columns or t.columns)))]


def row(table_name, **where) -> dict:
	found = rows(table_name, **where)
	assert len(found) == 1, f"expected exactly one {table_name} row matching {where}, found {len(found)}"
	return found[0]


def insert(table_name, **values) -> dict:
	t = table(table_name)
	with engine().begin() as conn:
		return dict(conn.execute(t.insert().values(**values).returning(t)).one()._mapping)


def update(table_name, where: dict, **values) -> int:
	t = table(table_name)
	with engine().begin() as conn:
		return conn.execute(t.update().where(*_where(t, where)).values(**values)).rowcount


def delete(table_name, **where) -> int:
	t = table(table_name)
	with engine().begin() as conn:
		return conn.execute(t.delete().where(*_where(t, where))).rowcount


class _Any:
	def __eq__(self, other):
		return True

	def __repr__(self):
		return "ANY"


ANY = _Any()


@dataclass
class Diff:
	'''
	Row-level changes between two snapshots, keyed by table name. Rows are identified by a key tuple: their `id` column where the table has one (`users` is keyed by username in the schema, but ids are what tests hold), else the primary key, else the whole row plus an occurrence index for duplicates (so changing such a row shows up as a delete plus an insert). Deleting and reinserting a row with the same key is indistinguishable from updating it.
	'''
	inserted: dict[str, list[dict]] = field(default_factory=dict)
	updated: dict[str, dict[tuple, dict]] = field(default_factory=dict)
	deleted: dict[str, list[tuple]] = field(default_factory=dict)

	def assert_exactly(self, inserted=None, updated=None, deleted=None):
		'''
		Fails on any change not described.

		`inserted`: {table: [partial row, ...]} — the listed rows and the inserted rows must pair up one-to-one, each pair matching on the listed columns. Unlisted columns are unchecked.
		`updated`: {table: {key: {column: new value}}} — the changed columns must be exactly these (a single-column key may be given bare).
		`deleted`: {table: [key, ...]}.
		'''
		for name, wants in (inserted or {}).items():
			for want in wants:
				_check_columns(name, want)
		for name, by_pk in (updated or {}).items():
			for changes in by_pk.values():
				_check_columns(name, changes)
		problems = []
		problems += _check_inserted(self.inserted, inserted or {})
		problems += _check_updated(self.updated, updated or {})
		problems += _check_deleted(self.deleted, deleted or {})
		assert not problems, "database changes differ from expected:\n" + "\n".join(problems)


def _check_columns(table_name, values: dict):
	unknown = set(values) - set(table(table_name).columns.keys())
	assert not unknown, f"{table_name} has no columns {sorted(unknown)}"


def _pk_tuple(pk):
	return pk if isinstance(pk, tuple) else (pk,)


def _sorted_keys(keys):
	return sorted(keys, key=repr)


def _matches(row, want):
	return all(row[k] == v for k, v in want.items())


def _pair_up(wants, rows):
	'''A one-to-one assignment of expectations to rows (bipartite matching by augmenting paths), or None.'''
	row_for_want: dict[int, int] = {}
	want_for_row: dict[int, int] = {}

	def assign(w, seen):
		for r, row in enumerate(rows):
			if r in seen or not _matches(row, wants[w]):
				continue
			seen.add(r)
			if r not in want_for_row or assign(want_for_row[r], seen):
				row_for_want[w], want_for_row[r] = r, w
				return True
		return False

	if len(wants) != len(rows) or not all(assign(w, set()) for w in range(len(wants))):
		return None
	return row_for_want


def _check_inserted(actual, expected):
	problems = []
	for name in sorted(set(actual) | set(expected)):
		wants, rows = expected.get(name, []), actual.get(name, [])
		if _pair_up(wants, rows) is None:
			problems.append(f"  {name}: inserted rows don't pair up with expectations\n    expected: {wants}\n    inserted: {rows}")
	return problems


def _check_updated(actual, expected):
	problems = []
	for name in sorted(set(actual) | set(expected)):
		want_rows = {_pk_tuple(pk): changes for pk, changes in expected.get(name, {}).items()}
		got_rows = actual.get(name, {})
		for pk in _sorted_keys(set(got_rows) | set(want_rows)):
			got, want = got_rows.get(pk, {}), want_rows.get(pk, {})
			if set(got) != set(want) or any(got[k] != want[k] for k in want):
				problems.append(f"  {name} {pk}: changed {got}, expected {want}")
	return problems


def _check_deleted(actual, expected):
	problems = []
	for name in sorted(set(actual) | set(expected)):
		got = _sorted_keys(actual.get(name, []))
		want = _sorted_keys(_pk_tuple(pk) for pk in expected.get(name, []))
		if got != want:
			problems.append(f"  {name}: deleted {got}, expected {want}")
	return problems


def _snapshot() -> dict[str, dict[tuple, dict]]:
	snap = {}
	with engine().connect() as conn:
		for t in _reflected().sorted_tables:
			key_cols = [t.c.id] if "id" in t.c else list(t.primary_key.columns)
			rows = {}
			for r in conn.execute(select(t)):
				row = dict(r._mapping)
				if key_cols:
					key = tuple(row[c.name] for c in key_cols)
				else:
					content = tuple(row[c.name] for c in t.columns)
					key = content + (sum(1 for k in rows if k[:-1] == content),)
				rows[key] = row
			snap[t.name] = rows
	return snap


@contextmanager
def db_diff():
	'''Captures every row-level change made inside the block; call `assert_exactly` on the result afterwards.'''
	before = _snapshot()
	diff = Diff()
	yield diff
	after = _snapshot()
	for name in after:
		b, a = before.get(name, {}), after[name]
		ins = [a[key] for key in a.keys() - b.keys()]
		dels = list(b.keys() - a.keys())
		upd = {}
		for key in a.keys() & b.keys():
			changes = {k: v for k, v in a[key].items() if b[key][k] != v}
			if changes:
				upd[key] = changes
		if ins:
			diff.inserted[name] = ins
		if dels:
			diff.deleted[name] = dels
		if upd:
			diff.updated[name] = upd
