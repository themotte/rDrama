from sqlalchemy import *
from sqlalchemy.orm import relationship

from files.classes.base import CreatedBase
from files.helpers.lazy import lazy


class Vote(CreatedBase):
	__tablename__ = "votes"

	submission_id = Column(Integer, ForeignKey("submissions.id"), primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
	vote_type = Column(Integer, nullable=False)
	app_id = Column(Integer, ForeignKey("oauth_apps.id"))
	real = Column(Boolean, default=True, nullable=False)

	Index('votes_type_index', vote_type)
	Index('vote_user_index', user_id)

	user = relationship("User", lazy="subquery", viewonly=True)
	post = relationship("Submission", lazy="subquery", viewonly=True)

	def __repr__(self):
		return f"<{self.__class__.__name__}(id={self.id})>"

	@property
	@lazy
	def json_core(self):
		data={
			"user_id": self.user_id,
			"submission_id":self.submission_id,
			"vote_type":self.vote_type
			}
		return data

	@property
	@lazy
	def json(self):
		data=self.json_core
		data["user"]=self.user.json_core
		data["post"]=self.post.json_core
		return data


class CommentVote(CreatedBase):
	__tablename__ = "commentvotes"

	comment_id = Column(Integer, ForeignKey("comments.id"), primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
	vote_type = Column(Integer, nullable=False)
	app_id = Column(Integer, ForeignKey("oauth_apps.id"))
	real = Column(Boolean, default=True, nullable=False)
	created_timestampz = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

	Index('cvote_user_index', user_id)
	Index('commentvotes_comments_type_index', vote_type)

	user = relationship("User", lazy="subquery")
	comment = relationship("Comment", lazy="subquery", viewonly=True)

	def __repr__(self):
		return f"<{self.__class__.__name__}(id={self.id})>"

	@property
	@lazy
	def json_core(self):
		data={
			"user_id": self.user_id,
			"comment_id":self.comment_id,
			"vote_type":self.vote_type
			}
		return data

	@property
	@lazy
	def json(self):
		data=self.json_core
		data["user"]=self.user.json_core
		data["comment"]=self.comment.json_core
		return data
