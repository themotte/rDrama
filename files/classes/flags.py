from sqlalchemy import *
from sqlalchemy.orm import relationship
from files.__main__ import Base
from .mix_ins import *

class Flag(Base, Stndrd):

	__tablename__ = "flags"

	id = Column(Integer, primary_key=True)
	post_id = Column(Integer, ForeignKey("submissions.id"))
	user_id = Column(Integer, ForeignKey("users.id"))
	reason = Column(String(100))
	
	user = relationship("User", lazy = "joined", primaryjoin = "Flag.user_id == User.id", uselist = False)

	def __repr__(self):

		return f"<Flag(id={self.id})>"


class CommentFlag(Base, Stndrd):

	__tablename__ = "commentflags"

	id = Column(Integer, primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"))
	comment_id = Column(Integer, ForeignKey("comments.id"))
	reason = Column(String(100))
	
	user = relationship("User", lazy = "joined", primaryjoin = "CommentFlag.user_id == User.id", uselist = False)

	def __repr__(self):

		return f"<CommentFlag(id={self.id})>"
