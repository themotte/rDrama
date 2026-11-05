from contextlib import contextmanager
from typing import Optional

from flask import g
from sqlalchemy import select, update
from sqlalchemy.orm import Query, aliased
from sqlalchemy.sql.expression import alias, func, text

from files.classes import Comment, Notification, Submission, Subscription, User
from files.classes.visstate import StateMod
from files.helpers.alerts import NOTIFY_USERS
from files.helpers.config.const import SORTS_COMMENTS

def comment_counted(comment:Comment) -> bool:
	'''Whether the comment counts toward its post's and its ancestors' comment counts: a comment on a post that others can see.'''
	return bool(comment.parent_submission) and comment.state_mod == StateMod.VISIBLE and comment.state_user_deleted_utc is None and not comment.author.shadowbanned


def comment_published(comment:Comment) -> bool:
	'''Whether the comment has been offered to others, so that it notifies: counted, and not on a draft.'''
	return comment_counted(comment) and not comment.post.private


def comment_sort(requested:Optional[str], v:Optional[User]) -> str:
	'''The comment order a page asks for, or the viewer's default when it names none we know ("new" for visitors).'''
	if requested in SORTS_COMMENTS: return requested
	return v.defaultsortingcomments if v else "new"


_SUBTREE_IDS_SQL = text("""
WITH RECURSIVE subtree(id, depth) AS (
		SELECT id, 0 FROM comments WHERE id = :cid
	UNION ALL
		SELECT c.id, s.depth + 1
		FROM comments c JOIN subtree s ON c.parent_comment_id = s.id
		WHERE s.depth < :depth
)
SELECT id FROM subtree
""")


def comment_subtree_ids(cid:int, depth:int) -> list[int]:
	'''Ids of the comment and its replies down to `depth` levels below it.'''
	return [row[0] for row in g.db.execute(_SUBTREE_IDS_SQL, {"cid": cid, "depth": depth})]


@contextmanager
def comment_state_change(comment:Comment):
	'''Wraps a change to whether others can see `comment`: publishes it when it starts counting and unpublishes it when it stops, and recounts its author's comments.'''
	was_counted = comment_counted(comment)
	yield
	is_counted = comment_counted(comment)
	if is_counted and not was_counted: comment_on_publish(comment)
	elif was_counted and not is_counted: comment_on_unpublish(comment)
	update_author_comment_count(comment)


_AUTHOR_COUNTED_SQL = "author_id = :author AND parent_submission IS NOT NULL AND state_mod = 'VISIBLE' AND state_user_deleted_utc IS NULL"

_AUTHOR_POST_DELTAS_SQL = text(f"""
SELECT parent_submission, count(*) FROM comments WHERE {_AUTHOR_COUNTED_SQL} GROUP BY parent_submission ORDER BY parent_submission
""")

_AUTHOR_ANCESTOR_DELTAS_SQL = text(f"""
WITH RECURSIVE up(ancestor) AS (
		SELECT parent_comment_id FROM comments WHERE {_AUTHOR_COUNTED_SQL} AND parent_comment_id IS NOT NULL
	UNION ALL
		SELECT c.parent_comment_id FROM comments c JOIN up ON c.id = up.ancestor WHERE c.parent_comment_id IS NOT NULL
)
SELECT ancestor, count(*) FROM up GROUP BY ancestor ORDER BY ancestor
""")


def comment_counts_shift_for_author(author_id:int, sign:int):
	'''Adds (sign +1) or subtracts (-1) all the author's comments that others could see, but for the author's shadowban, to the counts of their posts and ancestors: one update for the posts, one for the comments, each locking its rows in id order first. Call it before changing the author's row, so that, like publishing a comment, it locks posts before the user.'''
	g.db.flush()
	for table, column, deltas_sql in (("submissions", "comment_count", _AUTHOR_POST_DELTAS_SQL), ("comments", "descendant_count", _AUTHOR_ANCESTOR_DELTAS_SQL)):
		deltas = g.db.execute(deltas_sql, {"author": author_id}).all()
		if not deltas: continue
		ids, counts = [row[0] for row in deltas], [sign * row[1] for row in deltas]
		g.db.execute(text(f"SELECT id FROM {table} WHERE id = ANY(:ids) ORDER BY id FOR UPDATE"), {"ids": ids})
		g.db.execute(text(f"UPDATE {table} SET {column} = {column} + d.delta FROM unnest(CAST(:ids AS integer[]), CAST(:deltas AS integer[])) AS d(id, delta) WHERE {table}.id = d.id"), {"ids": ids, "deltas": counts})


def update_stateful_counters(comment, delta):
	"""
	When a comment changes publish status, we need to update all affected stateful
	comment counters (post comment count, ancestors' descendant counts)
	"""
	update_post_comment_count(comment, delta)
	update_ancestor_descendant_counts(comment, delta)

def update_post_comment_count(comment, delta):
	g.db.execute(update(Submission).where(Submission.id == comment.parent_submission).values(comment_count=Submission.comment_count + delta))

def update_author_comment_count(comment):
	'''Recounts the author's comments that count toward their own count: visible and not deleted, on published posts (whatever their shadowban).'''
	# The session doesn't autoflush, so the count would miss this comment's pending state change.
	g.db.flush()
	comment.author.comment_count = g.db.query(Comment).join(Submission, Submission.id == Comment.parent_submission).filter(
		Comment.author_id == comment.author_id,
		Comment.state_mod == StateMod.VISIBLE,
		Comment.state_user_deleted_utc == None,
		Submission.private == False,
	).count()
	g.db.add(comment.author)

def update_ancestor_descendant_counts(comment, delta):
	if comment.parent_comment_id is None:
		return

	# Use a recursive CTE to find all ancestors and update in one query,
	# instead of walking the parent chain one lazy load at a time.
	base = select(Comment.id, Comment.parent_comment_id).where(
		Comment.id == comment.parent_comment_id
	).cte(name='ancestors', recursive=True)

	base = base.union_all(
		select(Comment.id, Comment.parent_comment_id).where(
			Comment.id == base.c.parent_comment_id
		)
	)

	g.db.execute(
		update(Comment)
		.where(Comment.id.in_(select(base.c.id)))
		.values(descendant_count=Comment.descendant_count + delta)
		.execution_options(synchronize_session=False)
	)

def bulk_recompute_descendant_counts(predicate = None, db=None):
	"""
	Recomputes the descendant_count of a large number of comments.

	The descendant_count of a comment is equal to the number of direct visible child comments
	plus the sum of the descendant_count of those visible child comments.

	:param predicate: If set, only update comments matching this predicate
	:param db: If set, use this instead of g.db

	So for example

		>>> bulk_update_descendant_counts()

	will update all comments, while

		>>> bulk_update_descendant_counts(lambda q: q.where(Comment.parent_submission == 32)

	will only update the descendant counts of comments where parent_submission=32

	Internally, how this works is
		1. Find the maximum level of comments matching the predicate
		2. Starting from that level and going down, for each level update the descendant_counts

	Since the comments at the max level will always have 0 children, this means that we will perform
	`level` updates to update all comments.

	The update query looks like

		UPDATE comments
		SET descendant_count=descendant_counts.descendant_count
		FROM (
			SELECT
				parent_comments.id AS id,
				coalesce(sum(child_comments.descendant_count + 1), 0) AS descendant_count
			FROM comments AS parent_comments
				LEFT OUTER JOIN comments AS child_comments ON parent_comments.id = child_comments.parent_comment_id
			GROUP BY parent_comments.id
		) AS descendant_counts
		WHERE comments.id = descendant_counts.id
			AND comments.level = :level_1
			<predicate goes here>
	"""
	db = db if db is not None else g.db
	max_level_query = select(func.max(Comment.level))
	if predicate:
		max_level_query = predicate(max_level_query)

	max_level = db.execute(max_level_query).scalar()

	if max_level is None:
		max_level = 0

	for level in range(max_level, 0, -1):
		parent_comments = alias(Comment, name="parent_comments")
		child_comments = alias(Comment, name="child_comments")
		descendant_counts = aliased(
			Comment,
			(
				select(parent_comments)
				.outerjoin(
					child_comments,
					parent_comments.corresponding_column(Comment.id) == child_comments.corresponding_column(Comment.parent_comment_id)
				)
				.group_by(parent_comments.corresponding_column(Comment.id))
				.with_only_columns(
					parent_comments.corresponding_column(Comment.id),
					func.coalesce(
						func.sum(child_comments.corresponding_column(Comment.descendant_count) + text(str(1))),
						text(str(0))
					).label('descendant_count')
				)
				.subquery(name='descendant_counts')
			),
			adapt_on_names=True
		)
		update_statement = (
			update(Comment)
			.values(descendant_count=descendant_counts.descendant_count)
			.execution_options(synchronize_session=False)
			.where(Comment.id == descendant_counts.id)
			.where(Comment.level == level)
		)
		if predicate:
			update_statement = predicate(update_statement)
		db.execute(update_statement)
	db.commit()

def comment_on_publish(comment:Comment):
	'''Run when the comment starts counting (see comment_counted): when it's made, approved or restored. Counts it and notifies those it concerns.'''
	# A draft's comments notify when the draft is published
	if not comment.post.private:
		_notify_on_publish(comment)

	update_stateful_counters(comment, +1)

def _notify_on_publish(comment:Comment):
	'''Notifies those a newly published comment concerns: users it mentions, the post's subscribers and the author of what it replies to.'''
	author = comment.author
	# Generate notifs for: mentions, post subscribers, parent post/comment
	to_notify = NOTIFY_USERS(comment.body, comment.author)
	post_subscribers = g.db.query(Subscription.user_id).filter(
			Subscription.submission_id == comment.parent_submission,
			Subscription.user_id != comment.author_id,
		).all()
	to_notify.update([x[0] for x in post_subscribers])
	parent = comment.parent
	if parent and parent.author_id != comment.author_id and not parent.author.is_blocking(author):
		to_notify.add(parent.author_id)
	for uid in to_notify:
		notif = g.db.query(Notification) \
					.filter_by(comment_id=comment.id, user_id=uid).one_or_none()
		if not notif:
			notif = Notification(comment_id=comment.id, user_id=uid)
			g.db.add(notif)


def comments_on_draft_publish(post):
	'''Sends the notifications a draft's published comments held back while it was a draft, and counts its comments toward their authors' counts.'''
	comments = g.db.query(Comment).join(User, User.id == Comment.author_id).filter(
		Comment.parent_submission == post.id,
		Comment.state_mod == StateMod.VISIBLE,
		Comment.state_user_deleted_utc == None,
		User.shadowbanned == None,
	).order_by(Comment.id)
	for comment in comments:
		_notify_on_publish(comment)
	for comment in g.db.query(Comment).filter(Comment.parent_submission == post.id).distinct(Comment.author_id):
		update_author_comment_count(comment)


def comment_on_unpublish(comment:Comment):
	'''Run when the comment stops counting: when it's removed or deleted.'''
	update_stateful_counters(comment, -1)


def comment_filter_moderated(q: Query, v: Optional[User]) -> Query:
	if not (v and v.shadowbanned) and not (v and v.admin_level >= 3):
		q = q.join(User, User.id == Comment.author_id) \
		     .filter(User.shadowbanned == None)
	if not v or v.admin_level < 2:
		q = q.filter(
			(Comment.state_mod == StateMod.VISIBLE)
			| (Comment.author_id == ((v and v.id) or 0))
		)
	return q
