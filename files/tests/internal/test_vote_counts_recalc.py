'''
The vote_counts_recalc command recounts every vote counter by its definition (see spec/votes/test_counters.py), for correcting counts kept by older code. It writes only the rows whose counts are wrong, and leaves private messages as they are.
'''
from files.tests.spec.harness import assert_cli_ok, cli, db, factories

_COUNTED = "NOT EXISTS (SELECT 1 FROM users u WHERE u.id = v.user_id AND u.shadowbanned IS NOT NULL)"


def _xmin(table, row_id):
	'''The row's version: it changes whenever the row is written.'''
	return db.execute(f"SELECT xmin::text FROM {table} WHERE id = :id", id=row_id)


def _expected(table, votes, key, item_id):
	return tuple(db.execute(f"SELECT count(*) FROM {votes} v WHERE v.{key} = :id AND {condition}", id=item_id) for condition in (f"v.vote_type = 1 AND {_COUNTED}", f"v.vote_type = -1 AND {_COUNTED}", "v.vote_type = 1 AND v.real"))


def _truescore(user_id):
	return db.execute(f"""
		SELECT coalesce(sum(x.vote_type), 0) FROM (
			SELECT s.author_id, v.vote_type FROM votes v JOIN submissions s ON s.id = v.submission_id WHERE v.user_id != s.author_id AND {_COUNTED}
			UNION ALL
			SELECT c.author_id, v.vote_type FROM commentvotes v JOIN comments c ON c.id = v.comment_id WHERE c.parent_submission IS NOT NULL AND v.user_id != c.author_id AND {_COUNTED}
		) x WHERE x.author_id = :id
	""", id=user_id)


def test_recalc_corrects_every_counter_and_writes_only_wrong_rows():
	shadowbanned, voter, author, bystander = factories.user(shadowbanned="somemod"), factories.user(), factories.user(), factories.user()
	post = factories.post(author)
	comment = factories.comment(author, post)
	for who, vote in ((shadowbanned, 1), (voter, -1)):
		factories.vote(who, post, vote)
		factories.vote(who, comment, -vote)
	# An old shadowbanned vote, counted and marked real as older code left it
	db.execute("INSERT INTO votes (user_id, submission_id, vote_type, real) VALUES (:user, :post, 1, true)", user=factories.user(shadowbanned="somemod")["id"], post=post["id"])
	message = factories.message(author, voter, created_utc=1000)
	db.insert("commentvotes", user_id=voter["id"], comment_id=message["id"], vote_type=-1, real=True)
	untouched_post = factories.post(bystander)
	untouched = factories.comment(bystander, untouched_post)
	db.update("submissions", {"id": post["id"]}, upvotes=99, downvotes=7, realupvotes=0)
	db.update("comments", {"id": comment["id"]}, upvotes=-2)
	db.update("users", {"id": author["id"]}, truescore=1234)
	db.update("users", {"id": voter["id"]}, truescore=-5)
	before = {(t, i): _xmin(t, i) for t, i in (("submissions", untouched_post["id"]), ("comments", untouched["id"]), ("comments", message["id"]), ("users", bystander["id"]))}

	r = cli("vote_counts_recalc")

	assert_cli_ok(r)
	for table, votes, key, item in (("submissions", "votes", "submission_id", post), ("comments", "commentvotes", "comment_id", comment), ("submissions", "votes", "submission_id", untouched_post), ("comments", "commentvotes", "comment_id", untouched)):
		row = db.row(table, id=item["id"])
		assert (row["upvotes"], row["downvotes"], row["realupvotes"]) == _expected(table, votes, key, item["id"]), f"{table} {item['id']}"
	for user in (author, voter, bystander, shadowbanned):
		assert db.row("users", id=user["id"])["truescore"] == _truescore(user["id"]), f"user {user['id']}"
	assert (db.row("comments", id=message["id"])["upvotes"], db.row("comments", id=message["id"])["downvotes"]) == (1, 0)
	assert {key: _xmin(*key) for key in before} == before
	assert "Corrected 1 posts, 1 comments and 2 users" in r.output
