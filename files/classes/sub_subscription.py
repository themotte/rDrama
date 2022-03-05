from sqlalchemy import *
from sqlalchemy.orm import relationship
from files.__main__ import Base

class SubSubscription(Base):

	__tablename__ = "sub_subscriptions"
	user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
	sub = Column(String, ForeignKey("subs.name"), primary_key=True)

	def __repr__(self):
		return f"<SubSubscription(user_id={self.user_id}, sub={self.sub})>"