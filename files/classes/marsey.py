from sqlalchemy import *
from files.__main__ import Base

class Marsey(Base):
	__tablename__ = "marseys"

	name = Column(String, primary_key=True)
	author = Column(Integer, ForeignKey("users.id"))
	tags = Column(String, ForeignKey("users.id"))
	count = Column(Integer)

	def __repr__(self):
		return f"<Marsey(name={self.name})>"