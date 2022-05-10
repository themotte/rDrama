import time
from flask import *
from sqlalchemy import *
from sqlalchemy.orm import relationship
from files.__main__ import Base
from files.helpers.const import *

class UserNote(Base):

	__tablename__ = "usernotes"

	id = Column(Integer, primary_key=True)
	author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
	created_utc = Column(Integer, nullable=False)
	reference_user = Column(Integer, ForeignKey("users.id", ondelete='CASCADE'), nullable=False)
	reference_comment = Column(Integer, ForeignKey("comments.id", ondelete='SET NULL'))
	note = Column(String, nullable=False)

	author = relationship("User", foreign_keys='UserNote.author_id')
	user = relationship("User", foreign_keys='UserNote.reference_user', back_populates="notes")
	comment = relationship("Comment", back_populates="notes")
	
	def __init__(self, *args, **kwargs):
		if "created_utc" not in kwargs:
			kwargs["created_utc"] = int(time.time())
		super().__init__(*args, **kwargs)

	def __repr__(self):
		return f"<UserNote(id={self.id})>"