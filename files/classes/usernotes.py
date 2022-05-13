import time
from flask import *
from sqlalchemy import *
from sqlalchemy.orm import relationship
from files.__main__ import Base
from files.helpers.const import *
from enum import Enum
from sqlalchemy import Enum as EnumType

class UserTag(Enum):
    Quality = 0
    Good    = 1
    Comment = 2
    Warning = 3
    Tempban = 4
    Permban = 5
    Spam    = 6
    Bot     = 7

class UserNote(Base):

	__tablename__ = "usernotes"

	id = Column(Integer, primary_key=True)
	author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
	created_utc = Column(Integer, nullable=False)
	reference_user = Column(Integer, ForeignKey("users.id", ondelete='CASCADE'), nullable=False)
	reference_comment = Column(Integer, ForeignKey("comments.id", ondelete='SET NULL'))
	note = Column(String, nullable=False)
	tag = Column(EnumType(UserTag), nullable=False)

	author = relationship("User", foreign_keys='UserNote.author_id')
	user = relationship("User", foreign_keys='UserNote.reference_user', back_populates="notes")
	comment = relationship("Comment", back_populates="notes")
	
	def __init__(self, *args, **kwargs):
		if "created_utc" not in kwargs:
			kwargs["created_utc"] = int(time.time())
		super().__init__(*args, **kwargs)

	def __repr__(self):
		return f"<UserNote(id={self.id})>"

	def json(self):
		data = {'id': self.id,
				'author_name': self.author.username,
				'author_id': self.author.id,
				'user_name': self.user.username,
				'user_id': self.user.id,
				'created': self.created_utc,
				'comment_id': self.reference_comment,
				'note': self.note,
				'tag': self.tag.value
				}

		return data