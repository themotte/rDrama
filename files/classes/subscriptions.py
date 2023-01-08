from sqlalchemy.sql.schema import Column, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer
from files.classes.base import Base

class Subscription(Base):
	__tablename__ = "subscriptions"
	user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
	submission_id = Column(Integer, ForeignKey("submissions.id"), primary_key=True)
	
	Index('subscription_user_index', user_id)

	user = relationship("User", uselist=False, viewonly=True)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def __repr__(self):
		return f"<Subscription(id={self.id})>"
