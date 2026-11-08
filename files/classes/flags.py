from sqlalchemy import *
from sqlalchemy.orm import relationship
from files.classes.base import CreatedBase, CreatedDateTimeBase, Base
from files.helpers.config.const import *



class Flag(CreatedDateTimeBase):
	__tablename__ = "flags"

	id = Column(Integer, primary_key=True)
	post_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
	user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
	reason = Column(String)

	Index('flag_user_idx', user_id)

	user = relationship("User", primaryjoin = "Flag.user_id == User.id", uselist = False, viewonly=True)


class CommentFlag(CreatedDateTimeBase):
	__tablename__ = "commentflags"

	id = Column(Integer, primary_key=True)
	comment_id = Column(Integer, ForeignKey("comments.id"), nullable=False)
	user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
	reason = Column(String)

	Index('cflag_user_idx', user_id)

	user = relationship("User", primaryjoin = "CommentFlag.user_id == User.id", uselist = False, viewonly=True)
