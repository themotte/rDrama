from sqlalchemy import *
from sqlalchemy.sql import func
from files.classes.base import Base


class Alt(Base):
	__tablename__ = "alts"

	user1 = Column(Integer, ForeignKey("users.id"), primary_key=True)
	user2 = Column(Integer, ForeignKey("users.id"), primary_key=True)
	is_manual = Column(Boolean, nullable=False, default=False)

	__table_args__ = (
		Index('alts_user2_idx', user2),
		Index('alts_unique_combination', func.greatest(user1, user2), func.least(user1, user2), unique=True),
	)

	def __repr__(self):
		return f"<{self.__class__.__name__}(id={self.id})>"
