'''
Running a request while another transaction holds locks, to check what the request does when it has to wait.
'''
import contextlib
import threading
import time

from sqlalchemy import text

from files.helpers.locks import user_counts_lock
from files.tests.spec.harness import db

WAIT_SECONDS = 10


def _lock_waiters(conn) -> int:
	'''Backends of the test database other than `conn`'s that are waiting for a lock.'''
	return db.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock' AND pid != :pid", pid=conn.execute(text("SELECT pg_backend_pid()")).scalar())


@contextlib.contextmanager
def holding_transaction():
	'''An open transaction on a connection of its own, for the test to take locks in; run_while_held commits it. Closing the connection rolls back whatever it hasn't committed.'''
	with db.engine().connect() as conn:
		conn.execute(text("SET lock_timeout = '20s'"))
		yield conn


def hold_voting(conn, user_id):
	'''Takes in `conn`'s transaction the lock a vote by the user holds until it commits, besides the rows it writes.'''
	user_counts_lock(conn, [user_id])


def run_while_held(conn, request):
	'''
	Runs `request` (a function making one request) in a thread while `conn`'s transaction is open. Once the request is waiting for a lock, or WAIT_SECONDS have passed, the transaction commits, and the request's response is returned when it finishes.

	Returns (response, whether the request had to wait).
	'''
	outcome = {}

	def run():
		try:
			outcome["response"] = request()
		except BaseException as e:
			outcome["error"] = e

	thread = threading.Thread(target=run)
	thread.start()
	deadline = time.monotonic() + WAIT_SECONDS
	waited = False
	while time.monotonic() < deadline and thread.is_alive():
		if _lock_waiters(conn):
			waited = True
			break
		time.sleep(0.02)
	conn.commit()
	thread.join(WAIT_SECONDS * 3)
	assert not thread.is_alive(), "the request never finished"
	if "error" in outcome: raise outcome["error"]
	return outcome["response"], waited
