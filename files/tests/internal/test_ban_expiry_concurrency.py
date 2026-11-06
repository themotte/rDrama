'''
Requests that arrive together after a temporary ban ran out end it once: the user is told once.
'''
import time

from sqlalchemy import text

from files.tests.internal.concurrency import holding_transaction, run_all_while_held
from files.tests.spec.harness import as_user, assert_status, db, factories, seed


def test_concurrent_requests_end_an_expired_ban_once():
	user = factories.user(is_banned=seed.AUTOJANNY_ID, unban_utc=int(time.time()) - 60)
	requests = [lambda: as_user(user).get("/settings/profile") for _ in range(2)]

	with holding_transaction() as conn:
		conn.execute(text("SELECT 1 FROM users WHERE id = :id FOR UPDATE"), {"id": user["id"]})
		responses, waited = run_all_while_held(conn, requests)

	for r in responses: assert_status(r, 200)
	assert waited
	assert db.row("users", id=user["id"])["is_banned"] == 0
	assert len(db.rows("notifications", user_id=user["id"])) == 1
