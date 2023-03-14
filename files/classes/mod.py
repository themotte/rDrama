import time

from sqlalchemy.sql.schema import Column, ForeignKey, Index
from sqlalchemy.sql.sqltypes import Integer, String

from files.classes.base import Base
from files.helpers.lazy import *


class Mod(Base):

	__tablename__ = "mods"
	user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
	sub = Column(String, ForeignKey("subs.name"), primary_key=True)
	created_utc = Column(Integer, nullable=False)

	Index('fki_mod_sub_fkey', sub)

	def __init__(self, *args, **kwargs):
		if "created_utc" not in kwargs: kwargs["created_utc"] = int(time.time())
		super().__init__(*args, **kwargs)

	def __repr__(self):
		return f"<{self.__class__.__name__}(user_id={self.user_id}, sub={self.sub})>"

	@property
	@lazy
	def created_datetime(self):
		return time.strftime("%d/%B/%Y %H:%M:%S UTC", time.gmtime(self.created_utc))
