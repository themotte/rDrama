import time

from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import Column, ForeignKey, Index
from sqlalchemy.sql.sqltypes import Boolean, Integer

from files.classes.base import Base
from files.helpers.lazy import lazy


class Vote(Base):

	__tablename__ = "votes"

	submission_id = Column(Integer, ForeignKey("submissions.id"), primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
	vote_type = Column(Integer, nullable=False)
	app_id = Column(Integer, ForeignKey("oauth_apps.id"))
	real = Column(Boolean, default=True, nullable=False)
	created_utc = Column(Integer, nullable=False)

	Index('votes_type_index', vote_type)
	Index('vote_user_index', user_id)

	user = relationship("User", lazy="subquery", viewonly=True)
	post = relationship("Submission", lazy="subquery", viewonly=True)

	def __init__(self, *args, **kwargs):
		if "created_utc" not in kwargs: kwargs["created_utc"] = int(time.time())
		super().__init__(*args, **kwargs)

	def __repr__(self):
		return f"<Vote(id={self.id})>"

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


class CommentVote(Base):

	__tablename__ = "commentvotes"

	comment_id = Column(Integer, ForeignKey("comments.id"), primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
	vote_type = Column(Integer, nullable=False)
	app_id = Column(Integer, ForeignKey("oauth_apps.id"))
	real = Column(Boolean, default=True, nullable=False)
	created_utc = Column(Integer, nullable=False)

	Index('cvote_user_index', user_id)
	Index('commentvotes_comments_type_index', vote_type)

	user = relationship("User", lazy="subquery")
	comment = relationship("Comment", lazy="subquery", viewonly=True)

	def __init__(self, *args, **kwargs):
		if "created_utc" not in kwargs: kwargs["created_utc"] = int(time.time())
		super().__init__(*args, **kwargs)

	def __repr__(self):
		return f"<CommentVote(id={self.id})>"

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
