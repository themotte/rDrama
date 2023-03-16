from sqlalchemy import *
from files.classes.base import CreatedBase


class Alt(CreatedBase):
	__tablename__ = "alts"

	user1 = Column(Integer, ForeignKey("users.id"), primary_key=True)
	user2 = Column(Integer, ForeignKey("users.id"), primary_key=True)
	is_manual = Column(Boolean, nullable=False, default=False)

	Index('alts_user2_idx', user2)

	def __repr__(self):

		return f"<Alt(id={self.id})>"
