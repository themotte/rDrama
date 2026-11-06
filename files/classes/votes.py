from flask import g
from sqlalchemy import *
from sqlalchemy.orm import relationship

from files.classes.base import CreatedDateTimeBase


class Vote(CreatedDateTimeBase):
	__tablename__ = "votes"

	submission_id = Column(Integer, ForeignKey("submissions.id"), primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
	vote_type = Column(Integer, nullable=False)
	real = Column(Boolean, default=True, nullable=False)

	Index('votes_type_index', vote_type)
	Index('vote_user_index', user_id)

	user = relationship("User", lazy="subquery", viewonly=True)


class CommentVote(CreatedDateTimeBase):
	__tablename__ = "commentvotes"

	comment_id = Column(Integer, ForeignKey("comments.id"), primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
	vote_type = Column(Integer, nullable=False)
	real = Column(Boolean, default=True, nullable=False)

	Index('cvote_user_index', user_id)
	Index('commentvotes_comments_type_index', vote_type)

	user = relationship("User", lazy="subquery")


def votes_shown_to(target, v) -> tuple[int, int]:
	'''A post's or comment's (upvotes, downvotes) as `v` sees them: the counted ones, plus v's own vote when v is shadowbanned, since their votes count for no one else.'''
	ups, downs = target.upvotes, target.downvotes
	if not (v and v.shadowbanned): return ups, downs
	own = target.__dict__.get('voted')
	if own is None:
		vote_cls, key = (Vote, Vote.submission_id) if target.__tablename__ == 'submissions' else (CommentVote, CommentVote.comment_id)
		own = g.db.query(vote_cls.vote_type).filter(vote_cls.user_id == v.id, key == target.id).scalar() or 0
	return ups + (own == 1), downs + (own == -1)
