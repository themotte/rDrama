from sqlalchemy import *
from files.__main__ import Base

class Image(Base):
	__tablename__ = "images"
	id = Column(BigInteger, primary_key=True)
	state = Column(String)
	number = Column(Integer)
	text = Column(String)
	deletehash = Column(String)


class BadPic(Base):

	__tablename__="badpics"
	id = Column(BigInteger, primary_key=True)
	description=Column(String)
	phash=Column(String)
	ban_reason=Column(String)
	ban_time=Column(Integer)