from sqlalchemy import *
from files.__main__ import Base

class BadgeDef(Base):
	__tablename__ = "badge_defs"

	id = Column(Integer, primary_key=True)
	name = Column(String)
	description = Column(String)

	def __repr__(self):
		return f"<BadgeDef(id={self.id})>"