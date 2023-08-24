from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from files.classes.base import Base


class SaveRelationship(Base):
	__tablename__ = "save_relationship"

	user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
	submission_id: Mapped[int] = mapped_column(Integer, ForeignKey("submissions.id"), primary_key=True)

	Index('fki_save_relationship_submission_fkey', submission_id)


class CommentSaveRelationship(Base):
	__tablename__ = "comment_save_relationship"

	user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
	comment_id: Mapped[int] = mapped_column(Integer, ForeignKey("comments.id"), primary_key=True)

	Index('fki_comment_save_relationship_comment_fkey', comment_id)
