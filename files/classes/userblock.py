from sqlalchemy import *
from sqlalchemy.orm import relationship
from .mix_ins import *
from files.__main__ import Base

class UserBlock(Base, Stndrd, Age_times):

	__tablename__ = "userblocks"
	id = Column(Integer, primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"))
	target_id = Column(Integer, ForeignKey("users.id"))

	user = relationship(
		"User",
		innerjoin=True,
		primaryjoin="User.id==UserBlock.user_id")
	target = relationship(
		"User",
		innerjoin=True,
		primaryjoin="User.id==UserBlock.target_id")

	def __repr__(self):

		return f"<UserBlock(user={user.username}, target={target.username})>"
