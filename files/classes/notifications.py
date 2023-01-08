from sqlalchemy import Column, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Boolean, Integer
from files.classes.base import Base
import time

class Notification(Base):

	__tablename__ = "notifications"

	user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
	comment_id = Column(Integer, ForeignKey("comments.id"), primary_key=True)
	read = Column(Boolean, default=False, nullable=False)
	created_utc = Column(Integer, nullable=False)

	Index('notification_read_idx', read)
	Index('notifications_comment_idx', comment_id)
	Index('notifs_user_read_idx', user_id, read)

	comment = relationship("Comment", viewonly=True)
	user = relationship("User", viewonly=True)

	def __init__(self, *args, **kwargs):
		if "created_utc" not in kwargs: kwargs["created_utc"] = int(time.time())
		super().__init__(*args, **kwargs)

	def __repr__(self):
		return f"<Notification(id={self.id})>"
