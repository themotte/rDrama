from sqlalchemy.sql.schema import Column, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import Integer
from files.classes.base import Base
import time

class Follow(Base):
	__tablename__ = "follows"
	target_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
	created_utc = Column(Integer, nullable=False)

	Index('follow_user_id_index', user_id)

	user = relationship("User", uselist=False, primaryjoin="User.id==Follow.user_id", viewonly=True)
	target = relationship("User", primaryjoin="User.id==Follow.target_id", viewonly=True)

	def __init__(self, *args, **kwargs):
		if "created_utc" not in kwargs: kwargs["created_utc"] = int(time.time())
		super().__init__(*args, **kwargs)

	def __repr__(self):
		return f"<Follow(id={self.id})>"
