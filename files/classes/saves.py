from sqlalchemy import *
from sqlalchemy.orm import relationship
from files.classes.base import Base


class SaveRelationship(Base):
	__tablename__ = "save_relationship"

	user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
	submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), primary_key=True)

	Index('fki_save_relationship_submission_fkey', submission_id)

	user = relationship("User", viewonly=True)
	submission = relationship("Submission", viewonly=True)

	def __repr__(self):
		return f"<{self.__class__.__name__}(user_id={self.user_id}, submission_id={self.submission_id})>"


class CommentSaveRelationship(Base):
	__tablename__ = "comment_save_relationship"

	user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
	comment_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"), primary_key=True)

	Index('fki_comment_save_relationship_comment_fkey', comment_id)

	user = relationship("User", viewonly=True)
	comment = relationship("Comment", viewonly=True)

	def __repr__(self):
		return f"<{self.__class__.__name__}(user_id={self.user_id}, comment_id={self.comment_id})>"
