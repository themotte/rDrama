'''
The comment_counts_recalc command recounts every comment counter by its definition (see spec/comments/test_counters.py), for correcting counts kept by older code. It writes only the rows whose counts are wrong.
'''
from files.tests.spec.harness import assert_cli_ok, cli, db, factories

_COUNTED = "c.parent_submission IS NOT NULL AND c.state_mod = 'VISIBLE' AND c.state_user_deleted_utc IS NULL AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id = c.author_id AND u.shadowbanned IS NOT NULL)"


def _xmin(table, row_id):
	'''The row's version: it changes whenever the row is written.'''
	return db.execute(f"SELECT xmin::text FROM {table} WHERE id = :id", id=row_id)


def test_recalc_corrects_every_counter_and_writes_only_wrong_rows():
	shadowbanned, author, op = factories.user(shadowbanned="somemod"), factories.user(), factories.user()
	post = factories.post(op)
	top = factories.comment(author, post)
	removed = factories.comment(author, post, parent=top, state_mod="REMOVED", state_mod_set_by="somemod")
	visible = factories.comment(author, post, parent=removed)
	factories.comment(shadowbanned, post, parent=visible)
	factories.comment(author, post, parent=visible, state_user_deleted_utc="2020-01-01T00:00:00Z")
	draft = factories.post(op, private=True)
	factories.comment(author, draft)
	untouched_post = factories.post(op)
	untouched = factories.comment(op, untouched_post)
	db.update("submissions", {"id": post["id"]}, comment_count=99)
	db.update("comments", {"id": top["id"]}, descendant_count=99)
	db.update("comments", {"id": removed["id"]}, descendant_count=-3)
	db.update("users", {"id": author["id"]}, comment_count=99)
	before = {("submissions", untouched_post["id"]): _xmin("submissions", untouched_post["id"]), ("comments", untouched["id"]): _xmin("comments", untouched["id"]), ("users", op["id"]): _xmin("users", op["id"])}

	assert_cli_ok(cli("comment_counts_recalc"))

	for p in (post, draft, untouched_post):
		assert db.row("submissions", id=p["id"])["comment_count"] == db.execute(f"SELECT count(*) FROM comments c WHERE c.parent_submission = :p AND {_COUNTED}", p=p["id"])
		for comment in db.rows("comments", parent_submission=p["id"]):
			assert comment["descendant_count"] == db.execute(f"""
				WITH RECURSIVE below(id) AS (
					SELECT id FROM comments WHERE parent_comment_id = :id
					UNION ALL
					SELECT c.id FROM comments c JOIN below b ON c.parent_comment_id = b.id
				)
				SELECT count(*) FROM comments c WHERE c.id IN (SELECT id FROM below) AND {_COUNTED}
			""", id=comment["id"]), comment["id"]
	assert (db.row("submissions", id=post["id"])["comment_count"], db.row("comments", id=top["id"])["descendant_count"], db.row("comments", id=removed["id"])["descendant_count"]) == (2, 1, 1)
	assert db.row("users", id=author["id"])["comment_count"] == 2
	assert db.row("users", id=shadowbanned["id"])["comment_count"] == 1
	for (table, row_id), version in before.items():
		assert _xmin(table, row_id) == version, (table, row_id)
