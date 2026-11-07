'''
Which notifications and conversations a user is shown.
'''
from typing import Iterable

from flask import g

from sqlalchemy import and_, or_, true

from files.classes.comment import Comment
from files.classes.notifications import Notification
from files.classes.user import User
from files.classes.visstate import StateMod
from files.helpers.config.const import AUTOJANNY_ID, PERMS
from files.helpers.get import get_comment_trees_eager


def not_blocked_by(v: User):
	'''The SQL condition that a comment's author isn't someone `v` blocks, or that it's a message from an admin from level 2, who may message users blocking them.'''
	return or_(
		Comment.author_id.notin_(v.userblocks),
		and_(Comment.sentto != None, Comment.author.has(User.account_admin_level >= PERMS['POST_COMMENT_MODERATION'])),
	)


def with_threads(tops: Iterable[Comment], v: User) -> list[Comment]:
	'''The conversations whose first messages are `tops`, loaded whole for `v`: the first messages again, in order, each holding its answers oldest first.'''
	ids = [top.id for top in tops]
	if not ids: return []
	messages, _ = get_comment_trees_eager(lambda q: q.filter(or_(Comment.id.in_(ids), Comment.top_comment_id.in_(ids)), Comment.parent_submission == None), sort="old", v=v)
	loaded = {message.id: message for message in messages}
	return [loaded[i] for i in ids]


def mark_threads_read(tops: Iterable[Comment], v: User) -> None:
	'''Marks read `v`'s notifications of the messages they can see in the loaded conversations under `tops`, flagging the unread ones to show as such.'''
	seen, stack = {}, list(tops)
	while stack:
		message = stack.pop()
		if message.visibility_state.is_visible_to(v): seen[message.id] = message
		stack.extend(message.replies2 or [])
	if not seen: return
	for notification in g.db.query(Notification).filter(Notification.user_id == v.id, Notification.comment_id.in_(seen), Notification.read == False):
		seen[notification.comment_id].unread = True
		notification.read = True


def shown_notifications(query, v: User):
	'''
	`query` (over notifications joined to their comments) narrowed to `v`'s notifications that the notification pages show, of either kind:
	- of followed users' new posts (from AutoJanny), all of them;
	- of anything else, those whose comment is visible (not removed, held for approval or deleted, for admins too), by an author `v` doesn't block (`not_blocked_by`) and whose shadowban doesn't hide it from `v` (`shadowban_shown_to`).
	'''
	return query.filter(Notification.user_id == v.id, or_(
		Comment.author_id == AUTOJANNY_ID,
		and_(Comment.state_mod == StateMod.VISIBLE, Comment.state_user_deleted_utc == None, not_blocked_by(v), shadowban_shown_to(v)),
	))


def shadowban_shown_to(v: User):
	'''The SQL condition that a comment's author's shadowban doesn't hide it from `v`: the author isn't shadowbanned, or is `v`, or `v` is an admin from level 2.'''
	if v.admin_level >= PERMS['USER_SHADOWBAN']: return true()
	return or_(Comment.author_id == v.id, Comment.author.has(User.shadowbanned == None))
