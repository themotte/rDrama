'''
Which notifications and conversations a user is shown.
'''
from typing import Iterable

from flask import g

from sqlalchemy import and_, or_

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


def load_messages(condition, v: User) -> dict[int, Comment]:
	'''The messages meeting the SQL `condition`, loaded together for `v` and by id, each holding its loaded answers oldest first.'''
	messages, _ = get_comment_trees_eager(lambda q: q.filter(condition, Comment.parent_submission == None), sort="old", v=v)
	return {message.id: message for message in messages}


def with_threads(tops: Iterable[Comment], v: User) -> list[Comment]:
	'''The conversations whose first messages are `tops`, loaded whole for `v`: the first messages again, in order, each holding its answers.'''
	ids = [top.id for top in tops]
	if not ids: return []
	loaded = load_messages(or_(Comment.id.in_(ids), Comment.top_comment_id.in_(ids)), v)
	return [loaded[i] for i in ids]


def read_conversations(tops: Iterable[Comment], v: User) -> list[Comment]:
	'''The conversations whose first messages are `tops`, loaded whole for `v` (`with_threads`), with `v`'s notifications of what they show marked read.'''
	conversations = with_threads(tops, v)
	mark_threads_read(conversations, v)
	# The page renders from the loaded rows after this
	g.db.expire_on_commit = False
	g.db.commit()
	g.db.expire_on_commit = True
	return conversations


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
	- of anything else, those whose comment is visible (not removed, held for approval or deleted, for admins too), by an author `v` doesn't block (`not_blocked_by`) and whose shadowban doesn't hide it from `v` (`shadowban_shown_sql`).
	'''
	return query.filter(Notification.user_id == v.id, or_(
		Comment.author_id == AUTOJANNY_ID,
		and_(Comment.state_mod == StateMod.VISIBLE, Comment.state_user_deleted_utc == None, not_blocked_by(v), Comment.shadowban_shown_sql(v)),
	))

