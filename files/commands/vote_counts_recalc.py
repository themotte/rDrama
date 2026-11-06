import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from files.__main__ import app, db_session

# Over votes aliased "v": the vote counts, its voter not being shadowbanned
_COUNTED = "NOT EXISTS (SELECT 1 FROM users u WHERE u.id = v.user_id AND u.shadowbanned IS NOT NULL)"

_COUNTS = f"""
	count(*) FILTER (WHERE v.vote_type = 1 AND {_COUNTED}) AS ups,
	count(*) FILTER (WHERE v.vote_type = -1 AND {_COUNTED}) AS downs,
	count(*) FILTER (WHERE v.vote_type = 1 AND v.real) AS reals
"""

_POST_SQL = text(f"""
UPDATE submissions SET upvotes = counted.ups, downvotes = counted.downs, realupvotes = counted.reals
FROM (SELECT {_COUNTS} FROM votes v WHERE v.submission_id = :post) counted
WHERE submissions.id = :post AND (submissions.upvotes, submissions.downvotes, submissions.realupvotes) IS DISTINCT FROM (counted.ups, counted.downs, counted.reals)
""")

_COMMENTS_SQL = text(f"""
UPDATE comments SET upvotes = counted.ups, downvotes = counted.downs, realupvotes = counted.reals
FROM (
	SELECT c.id, {_COUNTS}
	FROM comments c LEFT JOIN commentvotes v ON v.comment_id = c.id
	WHERE c.parent_submission = :post
	GROUP BY c.id
) counted
WHERE comments.id = counted.id AND (comments.upvotes, comments.downvotes, comments.realupvotes) IS DISTINCT FROM (counted.ups, counted.downs, counted.reals)
""")

_USERS_SQL = text(f"""
UPDATE users SET truescore = counted.n
FROM (
	SELECT u.id, coalesce(sum(x.vote_type), 0) AS n
	FROM users u LEFT JOIN (
			SELECT s.author_id, v.vote_type FROM votes v JOIN submissions s ON s.id = v.submission_id WHERE v.user_id != s.author_id AND {_COUNTED}
		UNION ALL
			SELECT c.author_id, v.vote_type FROM commentvotes v JOIN comments c ON c.id = v.comment_id WHERE c.parent_submission IS NOT NULL AND v.user_id != c.author_id AND {_COUNTED}
	) x ON x.author_id = u.id
	GROUP BY u.id
) counted
WHERE users.id = counted.id AND users.truescore IS DISTINCT FROM counted.n
""")


def vote_counts_recalc(db: Session) -> dict[str, int]:
	'''
	Recounts the vote counts (upvotes, downvotes, realupvotes) of every post and every comment on a post, and every user's truescore, by their definitions (see spec/votes/test_counters.py), writing only the rows that differ. Private messages keep their counts. Commits after each post and its comments; the truescores are recounted in one statement at the end, which overwrites votes cast meanwhile, so run it when the site is quiet. Returns how many rows of each kind changed.
	'''
	changed = {"posts": 0, "comments": 0, "users": 0}
	post_ids = [row[0] for row in db.execute(text("SELECT id FROM submissions ORDER BY id"))]
	for i, post_id in enumerate(post_ids, 1):
		changed["posts"] += db.execute(_POST_SQL, {"post": post_id}).rowcount
		changed["comments"] += db.execute(_COMMENTS_SQL, {"post": post_id}).rowcount
		db.commit()
		if i % 1000 == 0: logging.info(f"Recounted {i} of {len(post_ids)} posts")
	changed["users"] = db.execute(_USERS_SQL).rowcount
	db.commit()
	return changed


@app.cli.command('vote_counts_recalc')
def vote_counts_recalc_cmd():
	'''Recount every vote counter (posts, comments, users' truescores) by its definition, e.g. once after deploying a fix to how they are kept.'''
	changed = vote_counts_recalc(db_session())
	print(f"Corrected {changed['posts']} posts, {changed['comments']} comments and {changed['users']} users")
