import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from files.__main__ import app, db_session
from files.helpers.comments import COMMENT_COUNTED_SQL as _COUNTED, COMMENT_SEEN_SQL

_POST_SQL = text(f"""
UPDATE submissions SET comment_count = counted.n
FROM (SELECT count(*) AS n FROM comments c WHERE c.parent_submission = :post AND {_COUNTED}) counted
WHERE submissions.id = :post AND submissions.comment_count IS DISTINCT FROM counted.n
""")

_DESCENDANTS_SQL = text(f"""
WITH RECURSIVE up(ancestor) AS (
		SELECT c.parent_comment_id FROM comments c WHERE c.parent_submission = :post AND c.parent_comment_id IS NOT NULL AND {_COUNTED}
	UNION ALL
		SELECT c.parent_comment_id FROM comments c JOIN up ON c.id = up.ancestor WHERE c.parent_comment_id IS NOT NULL
)
UPDATE comments SET descendant_count = counted.n
FROM (
	SELECT c.id, count(up.ancestor) AS n
	FROM comments c LEFT JOIN up ON up.ancestor = c.id
	WHERE c.parent_submission = :post
	GROUP BY c.id
) counted
WHERE comments.id = counted.id AND comments.descendant_count IS DISTINCT FROM counted.n
""")

_USERS_SQL = text(f"""
UPDATE users SET comment_count = counted.n
FROM (
	SELECT u.id, count(c.id) AS n
	FROM users u
	LEFT JOIN comments c ON c.author_id = u.id AND {COMMENT_SEEN_SQL}
		AND EXISTS (SELECT 1 FROM submissions s WHERE s.id = c.parent_submission AND NOT s.private)
	GROUP BY u.id
) counted
WHERE users.id = counted.id AND users.comment_count IS DISTINCT FROM counted.n
""")


def comment_counts_recalc(db: Session) -> dict[str, int]:
	'''
	Recounts every post's comment count, every comment's descendant count and every user's comment count by their definitions (see files.helpers.comments), writing only the rows that differ. Commits after each post, so the posts and comments it locks are held only briefly (the users are recounted in one statement at the end). A comment's visibility changing while its post is recounted can be lost, so run it when the site is quiet. Returns how many rows of each kind changed.
	'''
	changed = {"posts": 0, "comments": 0, "users": 0}
	post_ids = [row[0] for row in db.execute(text("SELECT id FROM submissions ORDER BY id"))]
	for i, post_id in enumerate(post_ids, 1):
		changed["posts"] += db.execute(_POST_SQL, {"post": post_id}).rowcount
		changed["comments"] += db.execute(_DESCENDANTS_SQL, {"post": post_id}).rowcount
		db.commit()
		if i % 1000 == 0: logging.info(f"Recounted {i} of {len(post_ids)} posts")
	changed["users"] = db.execute(_USERS_SQL).rowcount
	db.commit()
	return changed


@app.cli.command('comment_counts_recalc')
def comment_counts_recalc_cmd():
	'''Recount every comment counter (posts, comments, users) by its definition, e.g. once after deploying a fix to how they are kept.'''
	changed = comment_counts_recalc(db_session())
	print(f"Corrected {changed['posts']} posts, {changed['comments']} comments and {changed['users']} users")
