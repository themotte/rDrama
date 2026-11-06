'''
Votes cast while another vote's transaction is still open keep every vote: the counts and truescores they leave equal a recount.
'''
from sqlalchemy import text

from files.tests.internal.concurrency import holding_transaction, run_while_held
from files.tests.spec.harness import XHR, as_user, assert_status, db, factories


def _vote(voter, kind, item, vote):
	return lambda: as_user(voter).post(f"/vote/{kind}/{item['id']}/{vote}", headers=XHR)


def test_a_vote_waits_for_another_vote_on_the_same_item():
	author, first, second = factories.user(), factories.user(), factories.user()
	post = factories.post(author)
	client_request = _vote(second, "post", post, 1)

	with holding_transaction() as conn:
		conn.execute(text("INSERT INTO votes (user_id, submission_id, vote_type, real) VALUES (:user, :post, 1, true)"), {"user": first["id"], "post": post["id"]})
		conn.execute(text("UPDATE submissions SET upvotes = 2, realupvotes = 2 WHERE id = :post"), {"post": post["id"]})
		r, _ = run_while_held(conn, client_request)

	assert_status(r, 204)
	assert db.row("submissions", id=post["id"])["upvotes"] == 3


def test_a_users_vote_waits_for_their_own_first_vote_on_the_same_item():
	author, voter = factories.user(), factories.user()
	post = factories.post(author)

	with holding_transaction() as conn:
		conn.execute(text("INSERT INTO votes (user_id, submission_id, vote_type, real) VALUES (:user, :post, -1, true)"), {"user": voter["id"], "post": post["id"]})
		conn.execute(text("UPDATE submissions SET downvotes = 1 WHERE id = :post"), {"post": post["id"]})
		r, _ = run_while_held(conn, _vote(voter, "post", post, 1))

	assert_status(r, 204)
	assert db.row("votes", user_id=voter["id"], submission_id=post["id"])["vote_type"] == 1
	assert (db.row("submissions", id=post["id"])["upvotes"], db.row("submissions", id=post["id"])["downvotes"]) == (2, 0)

