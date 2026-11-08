'''
The nightly volunteer recalc locks the volunteers it writes in id order, as shadowbans do, so the two can't deadlock.
'''
import threading
import time

import pytest
from sqlalchemy import exc, text

from files.tests.internal.concurrency import WAIT_SECONDS, holding_transaction
from files.tests.spec.harness import assert_cli_ok, cli, db, factories


def _rater() -> dict:
	volunteer = factories.user()
	comment = factories.comment(factories.user(), factories.post(factories.user()))
	factories.assignment(volunteer, comment)
	factories.rating(volunteer, comment, "Ban")
	return volunteer


def _waiting(conn) -> bool:
	return db.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock' AND pid != :pid", pid=conn.execute(text("SELECT pg_backend_pid()")).scalar()) > 0


def test_the_recalc_waiting_for_a_volunteer_holds_none_after_them():
	first, second = _rater(), _rater()
	# Rewriting the first volunteer's row, an indexed column included so the new version can't stay in place, moves it after the second's, where a scan of the table finds it later
	db.update("users", {"id": first["id"]}, username=factories.unique("user"))
	outcome = {}

	def recalc():
		try:
			outcome["result"] = cli("volunteer_janitor_recalc")
		except BaseException as e:
			outcome["error"] = e

	with holding_transaction() as held, holding_transaction() as probe:
		held.execute(text("SELECT 1 FROM users WHERE id = :id FOR NO KEY UPDATE"), {"id": first["id"]})
		thread = threading.Thread(target=recalc)
		thread.start()
		deadline = time.monotonic() + WAIT_SECONDS
		while not _waiting(held) and time.monotonic() < deadline:
			time.sleep(0.02)
		waited = _waiting(held)
		try:
			probe.execute(text("SELECT 1 FROM users WHERE id = :id FOR NO KEY UPDATE NOWAIT"), {"id": second["id"]})
			second_free = True
		except exc.OperationalError:
			second_free = False
		probe.rollback()
		held.commit()
		thread.join(WAIT_SECONDS * 3)

	assert not thread.is_alive()
	if "error" in outcome: raise outcome["error"]
	assert_cli_ok(outcome["result"])
	assert (waited, second_free) == (True, True)
