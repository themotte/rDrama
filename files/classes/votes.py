from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship

from files.classes.base import CreatedDateTimeBase
from files.helpers.lazy import lazy


class Vote(CreatedDateTimeBase):
	__tablename__ = "votes"

	submission_id: Mapped[int] = mapped_column(Integer, ForeignKey("submissions.id"), primary_key=True)
	user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
	vote_type: Mapped[int] = mapped_column(Integer, nullable=False)
	app_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("oauth_apps.id"))
	real: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

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


class CommentVote(CreatedDateTimeBase):
	__tablename__ = "commentvotes"

	comment_id = mapped_column(Integer, ForeignKey("comments.id"), primary_key=True)
	user_id = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
	vote_type = mapped_column(Integer, nullable=False)
	app_id = mapped_column(Integer, ForeignKey("oauth_apps.id"))
	real = mapped_column(Boolean, default=True, nullable=False)

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
