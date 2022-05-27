from sqlalchemy import *
from sqlalchemy.orm import relationship
from files.__main__ import Base

class Exile(Base):

	__tablename__ = "exiles"
	user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
	sub = Column(String, ForeignKey("subs.name"), primary_key=True)
	exiler_id = Column(Integer, ForeignKey("users.id"), nullable=False)

	Index('fki_exile_exiler_fkey', exiler_id)
	Index('fki_exile_sub_fkey', sub)

	exiler = relationship("User", primaryjoin="User.id==Exile.exiler_id", viewonly=True)

	def __repr__(self):
		return f"<Exile(user_id={self.user_id}, sub={self.sub})>"
