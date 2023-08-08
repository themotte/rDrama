from sqlalchemy import *
from sqlalchemy.orm import relationship
from files.classes.base import CreatedDateTimeBase

class Notification(CreatedDateTimeBase):
	__tablename__ = "notifications"

	user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
	comment_id = Column(Integer, ForeignKey("comments.id"), primary_key=True)
	read = Column(Boolean, default=False, nullable=False)

	Index('notification_read_idx', read)
	Index('notifications_comment_idx', comment_id)
	Index('notifs_user_read_idx', user_id, read)

	comment = relationship("Comment", viewonly=True)
	user = relationship("User", viewonly=True)

	def __repr__(self):
		return f"<{self.__class__.__name__}(user_id={self.user_id}, comment_id={self.comment_id})>"
