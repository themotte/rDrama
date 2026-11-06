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
