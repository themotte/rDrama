from sqlalchemy import *
from sqlalchemy.orm import relationship
from files.classes.base import CreatedBase

class Follow(CreatedBase):
	__tablename__ = "follows"
	target_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)

	Index('follow_user_id_index', user_id)

	user = relationship("User", uselist=False, primaryjoin="User.id==Follow.user_id", viewonly=True)
	target = relationship("User", primaryjoin="User.id==Follow.target_id", viewonly=True)

	def __repr__(self):
		return f"<{self.__class__.__name__}(id={self.id})>"
