from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import Column, ForeignKey, Index
from sqlalchemy.sql.sqltypes import Integer, String

from files.classes.base import Base

# TODO: make them actual relationships

class SubBlock(Base):

	__tablename__ = "sub_blocks"
	user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
	sub = Column(String, ForeignKey("subs.name"), primary_key=True)

	Index('fki_sub_blocks_sub_fkey', sub)

	def __repr__(self):
		return f"<{self.__class__.__name__}(user_id={self.user_id}, sub={self.sub})>"
