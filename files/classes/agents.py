from sqlalchemy import *
from files.__main__ import Base

class Agent(Base):

	__tablename__ = "useragents"

	id = Column(Integer, primary_key=True)
	kwd = Column(String(64))
	reason = Column(String(256), default="")
	banned_by = Column(Boolean, ForeignKey("users.id"), default=True)
	mock = Column(String(256), default="")
	status_code = Column(Integer, default=418)
