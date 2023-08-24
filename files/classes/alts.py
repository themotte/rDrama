from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import text

from files.classes.base import Base


class Alt(Base):
	__tablename__ = "alts"

	user1: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
	user2: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
	is_manual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

	Index('alts_user2_idx', user2)
	Index('alts_unique_combination', 
		text('GREATEST(user1, user2)'), 
		text('LEAST(user1, user2)'), 
		unique=True
	)

	def __repr__(self):
		return f"<{self.__class__.__name__}(user1={self.user1}, user2={self.user2})>"
