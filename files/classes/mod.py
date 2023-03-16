from sqlalchemy import *
from sqlalchemy.orm import relationship
from files.classes.base import CreatedBase
from files.helpers.lazy import *

class Mod(CreatedBase):
	__tablename__ = "mods"
	user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
	sub = Column(String, ForeignKey("subs.name"), primary_key=True)

	Index('fki_mod_sub_fkey', sub)

	def __repr__(self):
		return f"<{self.__class__.__name__}(user_id={self.user_id}, sub={self.sub})>"
