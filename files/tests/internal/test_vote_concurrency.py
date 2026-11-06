'''
Votes cast while another vote's transaction is still open keep every vote: the counts and truescores they leave equal a recount.
'''
from sqlalchemy import text

from files.tests.internal.concurrency import hold_voting, holding_transaction, run_while_held
from files.tests.spec.harness import XHR, as_user, assert_json_message, assert_status, db, factories


def _vote(voter, kind, item, vote):
	return lambda: as_user(voter).post(f"/vote/{kind}/{item['id']}/{vote}", headers=XHR)


def test_a_vote_waits_for_another_vote_on_the_same_item():
	author, first, second = factories.user(), factories.user(), factories.user()
	post = factories.post(author)
	client_request = _vote(second, "post", post, 1)

	with holding_transaction() as conn:
		hold_voting(conn, first["id"])
		conn.execute(text("INSERT INTO votes (user_id, submission_id, vote_type, real) VALUES (:user, :post, 1, true)"), {"user": first["id"], "post": post["id"]})
		conn.execute(text("UPDATE submissions SET upvotes = 2, realupvotes = 2 WHERE id = :post"), {"post": post["id"]})
		r, waited = run_while_held(conn, client_request)

	assert_status(r, 204)
	assert waited
	assert db.row("submissions", id=post["id"])["upvotes"] == 3


def test_a_users_vote_waits_for_their_own_first_vote_on_the_same_item():
	author, voter = factories.user(), factories.user()
	post = factories.post(author)

	with holding_transaction() as conn:
		hold_voting(conn, voter["id"])
		conn.execute(text("INSERT INTO votes (user_id, submission_id, vote_type, real) VALUES (:user, :post, -1, true)"), {"user": voter["id"], "post": post["id"]})
		conn.execute(text("UPDATE submissions SET downvotes = 1 WHERE id = :post"), {"post": post["id"]})
		r, _ = run_while_held(conn, _vote(voter, "post", post, 1))

	assert_status(r, 204)
	assert db.row("votes", user_id=voter["id"], submission_id=post["id"])["vote_type"] == 1
	assert (db.row("submissions", id=post["id"])["upvotes"], db.row("submissions", id=post["id"])["downvotes"]) == (2, 0)


def test_a_vote_waits_for_another_vote_changing_the_same_authors_truescore():
	author, first, second = factories.user(), factories.user(), factories.user()
	held_post, voted_post = factories.post(author), factories.post(author)

	with holding_transaction() as conn:
		hold_voting(conn, first["id"])
		conn.execute(text("INSERT INTO votes (user_id, submission_id, vote_type, real) VALUES (:user, :post, 1, true)"), {"user": first["id"], "post": held_post["id"]})
		conn.execute(text("UPDATE users SET truescore = truescore + 1 WHERE id = :author"), {"author": author["id"]})
		r, waited = run_while_held(conn, _vote(second, "post", voted_post, 1))

	assert_status(r, 204)
	assert waited
	assert db.row("users", id=author["id"])["truescore"] == 2


def test_shadowbanning_doesnt_wait_for_votes_merely_referencing_its_rows():
	author = factories.user()
	post = factories.post(factories.user())
	factories.comment(author, post)
	admin = factories.admin(3)

	with holding_transaction() as conn:
		conn.execute(text("INSERT INTO votes (user_id, submission_id, vote_type, real) VALUES (:user, :post, 1, true)"), {"user": factories.user()["id"], "post": post["id"]})
		r, waited = run_while_held(conn, lambda: as_user(admin).post(f"/shadowban/{author['id']}", headers=XHR))

	assert_json_message(r)
	assert not waited
