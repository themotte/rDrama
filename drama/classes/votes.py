from flask import *
from time import time
from sqlalchemy import *
from sqlalchemy.orm import relationship
from drama.helpers.base36 import *
from drama.__main__ import Base

class Vote(Base):

	__tablename__ = "votes"

	id = Column(Integer, primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"))
	vote_type = Column(Integer)
	submission_id = Column(Integer, ForeignKey("submissions.id"))
	created_utc = Column(Integer, default=0)
	app_id = Column(Integer, ForeignKey("oauth_apps.id"))

	user = relationship("User", lazy="subquery")
	post = relationship("Submission", lazy="subquery")

	def __init__(self, *args, **kwargs):

		if "created_utc" not in kwargs:
			kwargs["created_utc"] = int(time())


		super().__init__(*args, **kwargs)

	def __repr__(self):
		return f"<Vote(id={self.id})>"

	def change_to(self, x):
		"""
		1 - upvote
		0 - novote
		-1 - downvote
		"""
		if x in ["-1", "0", "1"]:
			x = int(x)
		elif x not in [-1, 0, 1]:
			abort(400)

		self.vote_type = x
		self.created_utc = int(time())

		g.db.add(self)

	@property
	def json_core(self):
		data={
			"user_id": self.user_id,
			"submission_id":self.submission_id,
			"created_utc": self.created_utc,
			"vote_type":self.vote_type
			}
		return data

	@property
	def json(self):
		data=self.json_core
		data["user"]=self.user.json_core
		data["post"]=self.post.json_core
	
		return data


class CommentVote(Base):

	__tablename__ = "commentvotes"

	id = Column(Integer, primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"))
	vote_type = Column(Integer)
	comment_id = Column(Integer, ForeignKey("comments.id"))
	created_utc = Column(Integer, default=0)
	app_id = Column(Integer, ForeignKey("oauth_apps.id"))

	user = relationship("User", lazy="subquery")
	comment = relationship("Comment", lazy="subquery")

	def __init__(self, *args, **kwargs):
		if "created_utc" not in kwargs:
			kwargs["created_utc"] = int(time())


		super().__init__(*args, **kwargs)

	def __repr__(self):
		return f"<CommentVote(id={self.id})>"

	def change_to(self, x):
		"""
		1 - upvote
		0 - novote
		-1 - downvote
		"""
		if x in ["-1", "0", "1"]:
			x = int(x)
		elif x not in [-1, 0, 1]:
			abort(400)

		self.vote_type = x
		self.created_utc = int(time())

		g.db.add(self)

	@property
	def json_core(self):
		data={
			"user_id": self.user_id,
			"comment_id":self.comment_id,
			"created_utc": self.created_utc,
			"vote_type":self.vote_type
			}
		return data

	@property
	def json(self):
		data=self.json_core
		data["user"]=self.user.json_core
		data["comment"]=self.comment.json_core
	
		return data