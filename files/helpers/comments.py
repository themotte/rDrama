from files.classes import Comment, Notification, Subscription
from files.helpers.alerts import NOTIFY_USERS
from files.helpers.const import PUSHER_ID
from flask import g

def update_stateful_counters(comment, delta):
	"""
	When a comment changes publish status, we need to update all affected stateful
	comment counters (e.g. author comment count, post comment count)
	"""
	author = comment.author
	comment.post.comment_count += delta
	g.db.add(comment.post)

	comment.author.comment_count = g.db.query(Comment).filter(
		Comment.author_id == comment.author_id,
		Comment.parent_submission != None,
		Comment.is_banned == False,
		Comment.deleted_utc == 0,
	).count()
	g.db.add(comment.author)

def comment_on_publish(comment:Comment):
	"""
	Run when comment becomes visible: immediately for non-filtered comments,
	or on approval for previously filtered comments.
	Should be used to update stateful counters, notifications, etc. that
	reflect the comments users will actually see.
	"""
	# TODO: Get this out of the routes and into a model eventually...
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
	by changing the filter_state to "removed", or when the user deletes the comment.
	Should be used to update stateful counters, notifications, etc. that
	reflect the comments users will actually see.
	"""
	update_stateful_counters(comment, -1)
