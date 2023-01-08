from sqlalchemy.schema import Column, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer
from files.classes.base import Base

# TODO: make them actual relationships

class SaveRelationship(Base):

	__tablename__="save_relationship"

	user_id=Column(Integer, ForeignKey("users.id"), primary_key=True)
	submission_id=Column(Integer, ForeignKey("submissions.id"), primary_key=True)

	Index('fki_save_relationship_submission_fkey', submission_id)


class CommentSaveRelationship(Base):

	__tablename__="comment_save_relationship"

	user_id=Column(Integer, ForeignKey("users.id"), primary_key=True)
	comment_id=Column(Integer, ForeignKey("comments.id"), primary_key=True)

	Index('fki_comment_save_relationship_comment_fkey', comment_id)
