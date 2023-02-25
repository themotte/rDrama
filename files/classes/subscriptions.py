from sqlalchemy import *
from sqlalchemy.orm import relationship
from files.__main__ import Base

class Subscription(Base):
	__tablename__ = "subscriptions"
	user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
	submission_id = Column(Integer, ForeignKey("submissions.id"), primary_key=True)
	
	Index('subscription_user_index', user_id)

	user = relationship("User", uselist=False, viewonly=True)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def __repr__(self):
		return f"<{self.__class__.__name__}(id={self.id})>"
