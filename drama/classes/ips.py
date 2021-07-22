from sqlalchemy import *
from drama.__main__ import Base


class IP(Base):

	__tablename__ = "ips"

	id = Column(Integer, primary_key=True)
	addr = Column(String(64))
	reason = Column(String(256), default="")
	banned_by = Column(Integer, ForeignKey("users.id"), default=True)
	until_utc=Column(Integer, default=None)


class Agent(Base):

	__tablename__ = "useragents"

	id = Column(Integer, primary_key=True)
	kwd = Column(String(64))
	reason = Column(String(256), default="")
	banned_by = Column(Boolean, ForeignKey("users.id"), default=True)
	mock = Column(String(256), default="")
	status_code = Column(Integer, default=418)
