from collections import defaultdict
from typing import Optional, Union

from flask import g
from sqlalchemy import text

from files.classes import Comment, Submission, User
from files.classes.visstate import StateMod
from files.helpers.comments import comment_counts_of_authors, comment_state_change
from files.helpers.locks import user_counts_lock


def moderate(item:Union[Submission, Comment], state_mod:StateMod, by:str) -> int:
	'''
	Sets a post's or comment's moderation state on behalf of `by`, with the usual effects when that changes whether others can see it (counters, publish notifications, cached listings). Logs nothing.

	Returns 1 if the item became visible, -1 if it stopped being visible, else 0.
	'''
	was_visible = item.state_mod == StateMod.VISIBLE
	is_visible = state_mod == StateMod.VISIBLE

	if isinstance(item, Comment):
		with comment_state_change(item):
			item.state_mod = state_mod
			item.state_mod_set_by = by
	else:
		item.state_mod = state_mod
		item.state_mod_set_by = by
		if is_visible and not was_visible: item.publish()
		elif was_visible and not is_visible: item.visibility_changed()

	if is_visible and not was_visible: return 1
	if was_visible and not is_visible: return -1
	return 0


_VOTER_POST_DELTAS_SQL = text("""
SELECT v.submission_id, count(*) FILTER (WHERE v.vote_type = 1), count(*) FILTER (WHERE v.vote_type = -1)
FROM votes v WHERE v.user_id = ANY(:users) AND v.vote_type != 0 GROUP BY v.submission_id
""")

_VOTER_COMMENT_DELTAS_SQL = text("""
SELECT v.comment_id, count(*) FILTER (WHERE v.vote_type = 1), count(*) FILTER (WHERE v.vote_type = -1)
FROM commentvotes v JOIN comments c ON c.id = v.comment_id
WHERE v.user_id = ANY(:users) AND v.vote_type != 0 AND c.parent_submission IS NOT NULL GROUP BY v.comment_id
""")

_VOTER_TRUESCORE_DELTAS_SQL = text("""
SELECT x.author_id, sum(x.vote_type) FROM (
		SELECT s.author_id, v.user_id, v.vote_type FROM votes v JOIN submissions s ON s.id = v.submission_id
	UNION ALL
		SELECT c.author_id, v.user_id, v.vote_type FROM commentvotes v JOIN comments c ON c.id = v.comment_id WHERE c.parent_submission IS NOT NULL
) x WHERE x.user_id = ANY(:users) AND x.author_id != x.user_id GROUP BY x.author_id HAVING sum(x.vote_type) != 0
""")


def _counts_shift(user_ids:list[int], sign:int, lock_user_ids:list[int]):
	'''
	Adds (sign +1) or subtracts (-1) what the users' comments and votes add to the counts others see: their comments to their posts' comment counts and their ancestors' descendant counts, their votes to the vote counts of what they voted on and to its authors' truescores.

	Computes every change first, then locks the rows it changes table by table (posts, then comments, then users, each in id order, with `lock_user_ids` among the users), the order voting and commenting lock them in. Votes and comments on any of those rows wait until the transaction commits, which for a prolific user is a lot of rows.
	'''
	posts, comments = (defaultdict(lambda: [0, 0, 0]) for _ in range(2))
	post_comments, ancestors = comment_counts_of_authors(user_ids)
	for post_id, n in post_comments.items(): posts[post_id][0] += n
	for comment_id, n in ancestors.items(): comments[comment_id][0] += n
	for deltas, sql in ((posts, _VOTER_POST_DELTAS_SQL), (comments, _VOTER_COMMENT_DELTAS_SQL)):
		for item_id, ups, downs in g.db.execute(sql, {"users": user_ids}):
			deltas[item_id][1] += ups
			deltas[item_id][2] += downs
	truescores = dict(g.db.execute(_VOTER_TRUESCORE_DELTAS_SQL, {"users": user_ids}).all())

	for table, count_column, deltas in (("submissions", "comment_count", posts), ("comments", "descendant_count", comments)):
		if not deltas: continue
		ids = sorted(deltas)
		g.db.execute(text(f"SELECT id FROM {table} WHERE id = ANY(:ids) ORDER BY id FOR NO KEY UPDATE"), {"ids": ids})
		columns = {name: [sign * deltas[i][k] for i in ids] for k, name in enumerate((count_column, "upvotes", "downvotes"))}
		g.db.execute(text(f"""
			UPDATE {table} SET {count_column} = {count_column} + d.counted, upvotes = upvotes + d.ups, downvotes = downvotes + d.downs
			FROM unnest(CAST(:ids AS integer[]), CAST(:counted AS integer[]), CAST(:ups AS integer[]), CAST(:downs AS integer[])) AS d(id, counted, ups, downs)
			WHERE {table}.id = d.id
		"""), {"ids": ids, "counted": columns[count_column], "ups": columns["upvotes"], "downs": columns["downvotes"]})

	g.db.execute(text("SELECT id FROM users WHERE id = ANY(:ids) ORDER BY id FOR NO KEY UPDATE"), {"ids": sorted(set(truescores) | set(lock_user_ids))})
	if truescores:
		ids = sorted(truescores)
		g.db.execute(text("UPDATE users SET truescore = truescore + d.delta FROM unnest(CAST(:ids AS integer[]), CAST(:deltas AS integer[])) AS d(id, delta) WHERE users.id = d.id"), {"ids": ids, "deltas": [sign * truescores[i] for i in ids]})


def _shadowban_change(users:list[User], by:Optional[str]):
	'''Shadowbans `users` on behalf of `by`, or lifts their shadowbans (`by` None), shifting the counts others see by what their comments and votes add for those whose shadowban changes. Call it before changing the users' rows, so the rows are locked in order with the others.'''
	g.db.flush()
	ids = [user.id for user in users]
	# A vote or post by one of them, in flight, finishes first, and none starts until this commits
	user_counts_lock(g.db, ids)
	changing = [row[0] for row in g.db.execute(text("SELECT id FROM users WHERE id = ANY(:ids) AND (shadowbanned IS NULL) = :clear"), {"ids": ids, "clear": by is not None})]
	if changing: _counts_shift(changing, +1 if by is None else -1, ids)
	for user in users: user.shadowbanned = by


def shadowban_set(user:User, by:str) -> None:
	'''Shadowbans `user` on behalf of `by`, taking their comments and votes out of the counts others see. Logs nothing.'''
	_shadowban_change([user], by)


def shadowban_lift(users:list[User]) -> None:
	'''Lifts the users' shadowbans, counting their comments and votes again (without notifying anyone of their comments). Logs nothing.'''
	_shadowban_change(users, None)
