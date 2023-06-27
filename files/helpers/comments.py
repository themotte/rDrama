from sys import stdout
from typing import Optional

import gevent
from flask import g, request
from pusher_push_notifications import PushNotifications
from sqlalchemy import select, update
from sqlalchemy.orm import Query, aliased
from sqlalchemy.sql.expression import alias, func, text

from files.classes import Comment, Notification, Subscription, User
from files.classes.visstate import StateMod
from files.helpers.alerts import NOTIFY_USERS
from files.helpers.assetcache import assetcache_path
from files.helpers.config.environment import (PUSHER_ID, PUSHER_KEY, SITE_FULL,
                                              SITE_ID)

if PUSHER_ID != 'blahblahblah':
	beams_client = PushNotifications(instance_id=PUSHER_ID, secret_key=PUSHER_KEY)

def pusher_thread(interests, c, username):
	if len(c.body) > 500: notifbody = c.body[:500] + '...'
	else: notifbody = c.body

	beams_client.publish_to_interests(
		interests=[interests],
		publish_body={
			'web': {
				'notification': {
					'title': f'New reply by @{username}',
					'body': notifbody,
					'deep_link': f'{SITE_FULL}/comment/{c.id}?context=8&read=true#context',
					'icon': SITE_FULL + assetcache_path(f'images/{SITE_ID}/icon.webp'),
				}
			},
			'fcm': {
				'notification': {
					'title': f'New reply by @{username}',
					'body': notifbody,
				},
				'data': {
					'url': f'/comment/{c.id}?context=8&read=true#context',
				}
			}
		},
	)
	stdout.flush()


def update_stateful_counters(comment, delta):
	"""
	When a comment changes publish status, we need to update all affected stateful
	comment counters (e.g. author comment count, post comment count)
	"""
	update_post_comment_count(comment, delta)
	update_author_comment_count(comment, delta)
	update_ancestor_descendant_counts(comment, delta)

def update_post_comment_count(comment, delta):
	author = comment.author
	comment.post.comment_count += delta
	g.db.add(comment.post)

def update_author_comment_count(comment, delta):
	author = comment.author
	comment.author.comment_count = g.db.query(Comment).filter(
		Comment.author_id == comment.author_id,
		Comment.parent_submission != None,
		Comment.state_mod == StateMod.VISIBLE,
		Comment.state_user_deleted_utc == None,
	).count()
	g.db.add(comment.author)

def update_ancestor_descendant_counts(comment, delta):
	parent = comment.parent_comment_writable
	if parent is None:
		return
	parent.descendant_count += delta
	g.db.add(parent)
	update_ancestor_descendant_counts(parent, delta)

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
	max_level_query = db.query(func.max(Comment.level))
	if predicate:
		max_level_query = predicate(max_level_query)

	max_level = max_level_query.scalar()

	if max_level is None:
		max_level = 0

	for level in range(max_level, 0, -1):
		parent_comments = alias(Comment, name="parent_comments")
		child_comments = alias(Comment, name="child_comments")
		descendant_counts = aliased(
			Comment,
			(
				select(parent_comments)
				.join(
					child_comments,
					parent_comments.corresponding_column(Comment.id) == child_comments.corresponding_column(Comment.parent_comment_id),
					True
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
	"""
	Run when comment becomes visible: immediately for non-filtered comments,
	or on approval for previously filtered comments.
	Should be used to update stateful counters, notifications, etc. that
	reflect the comments users will actually see.
	"""
	author = comment.author

	# Shadowbanned users are invisible. This may lead to inconsistencies if
	# a user comments while shadowed and is later unshadowed. (TODO?)
	if author.shadowbanned:
		return

	# Comment instances used for purposes other than actual comments (notifs,
	# DMs) shouldn't be considered published.
	if not comment.parent_submission:
		return

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

	update_stateful_counters(comment, +1)

	# Generate push notifications if enabled.
	if PUSHER_ID != 'blahblahblah' and comment.author_id != parent.author_id:
		try:
			gevent.spawn(pusher_thread, f'{request.host}{parent.author.id}',
				comment, comment.author_name)
		except: pass

def comment_on_unpublish(comment:Comment):
	"""
	Run when a comment becomes invisible: when a moderator makes the comment non-visible
	by changing the state_mod to "removed", or when the user deletes the comment.
	Should be used to update stateful counters, notifications, etc. that
	reflect the comments users will actually see.
	"""
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
