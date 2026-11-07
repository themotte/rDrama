'''
Which notifications and conversations a user is shown.
'''
from typing import Iterable

from sqlalchemy import and_, or_

from files.classes.comment import Comment
from files.classes.user import User
from files.helpers.config.const import PERMS
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
