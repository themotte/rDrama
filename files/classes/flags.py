from sqlalchemy.sql.schema import Column, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer, String
from files.classes.base import Base
from files.helpers.lazy import lazy
from files.helpers.const import *
import time

class Flag(Base):

	__tablename__ = "flags"

	id = Column(Integer, primary_key=True)
	post_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
	user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
	reason = Column(String)
	created_utc = Column(Integer, nullable=False)

	Index('flag_user_idx', user_id)

	user = relationship("User", primaryjoin = "Flag.user_id == User.id", uselist = False, viewonly=True)

	def __init__(self, *args, **kwargs):
		if "created_utc" not in kwargs: kwargs["created_utc"] = int(time.time())
		super().__init__(*args, **kwargs)

	def __repr__(self):
		return f"<Flag(id={self.id})>"

	@property
	@lazy
	def created_date(self):
		return time.strftime("%d %B %Y", time.gmtime(self.created_utc))

	@property
	@lazy
	def created_datetime(self):
		return str(time.strftime("%d/%B/%Y %H:%M:%S UTC", time.gmtime(self.created_utc)))

	@lazy
	def realreason(self, v):
		return self.reason


class CommentFlag(Base):

	__tablename__ = "commentflags"

	id = Column(Integer, primary_key=True)
	comment_id = Column(Integer, ForeignKey("comments.id"), nullable=False)
	user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
	reason = Column(String)
	created_utc = Column(Integer, nullable=False)

	Index('cflag_user_idx', user_id)

	user = relationship("User", primaryjoin = "CommentFlag.user_id == User.id", uselist = False, viewonly=True)

	def __init__(self, *args, **kwargs):
		if "created_utc" not in kwargs: kwargs["created_utc"] = int(time.time())
		super().__init__(*args, **kwargs)

	def __repr__(self):
		return f"<CommentFlag(id={self.id})>"

	@property
	@lazy
	def created_date(self):
		return time.strftime("%d %B %Y", time.gmtime(self.created_utc))

	@property
	@lazy
	def created_datetime(self):
		return str(time.strftime("%d/%B/%Y %H:%M:%S UTC", time.gmtime(self.created_utc)))

	@lazy
	def realreason(self, v):
		return self.reason
