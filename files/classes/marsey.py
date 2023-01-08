from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import Column, ForeignKey, Index
from sqlalchemy.sql.sqltypes import Integer, String

from files.classes.base import Base


class Marsey(Base):
	__tablename__ = "marseys"

	name = Column(String, primary_key=True)
	author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
	tags = Column(String(length=200), nullable=False)
	count = Column(Integer, default=0, nullable=False)

	Index('marseys_idx2', author_id)
	Index('marseys_idx3', count.desc())
	Index('marseys_idx', name)

	def __repr__(self):
		return f"<Marsey(name={self.name})>"
