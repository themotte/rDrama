from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import Column, ForeignKey, Index
from sqlalchemy.sql.sqltypes import Integer

from files.classes.base import Base


class UserBlock(Base):

	__tablename__ = "userblocks"
	user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
	target_id = Column(Integer, ForeignKey("users.id"), primary_key=True)

	Index('block_target_idx', target_id)

	user = relationship("User", primaryjoin="User.id==UserBlock.user_id", viewonly=True)
	target = relationship("User", primaryjoin="User.id==UserBlock.target_id", viewonly=True)

	def __repr__(self):
		return f"<UserBlock(user={self.user_id}, target={self.target_id})>"
