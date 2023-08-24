from sqlalchemy import *
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped, mapped_column, relationship
from files.classes.base import Base

class Subscription(Base):
	__tablename__ = "subscriptions"
	user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
	submission_id: Mapped[int] = mapped_column(Integer, ForeignKey("submissions.id"), primary_key=True)
	
	Index('subscription_user_index', user_id)

	user = relationship("User", uselist=False, viewonly=True)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def __repr__(self):
		return f"<{self.__class__.__name__}(id={self.id})>"
