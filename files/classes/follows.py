from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship

from files.classes.base import CreatedDateTimeBase


class Follow(CreatedDateTimeBase):
	__tablename__ = "follows"
	target_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
	user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)

	Index('follow_user_id_index', user_id)

	user = relationship("User", uselist=False, primaryjoin="User.id==Follow.user_id", viewonly=True)
	target = relationship("User", primaryjoin="User.id==Follow.target_id", viewonly=True)

	def __repr__(self):
		return (
			f"<{self.__class__.__name__}("
			f"target_id={self.target_id}, user_id={self.user_id})>"
		)
