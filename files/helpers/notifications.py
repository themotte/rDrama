'''
Which notifications and conversations a user is shown.
'''
from sqlalchemy import and_, or_

from files.classes.comment import Comment
from files.classes.user import User
from files.helpers.config.const import PERMS


def not_blocked_by(v: User):
	'''The SQL condition that a comment's author isn't someone `v` blocks, or that it's a message from an admin from level 2, who may message users blocking them.'''
	return or_(
		Comment.author_id.notin_(v.userblocks),
		and_(Comment.sentto != None, Comment.author.has(User.account_admin_level >= PERMS['POST_COMMENT_MODERATION'])),
	)
