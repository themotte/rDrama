from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from files.classes.base import Base

class Marsey(Base):
	__tablename__ = "marseys"

	name: Mapped[str] = mapped_column(String, primary_key=True)
	author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
	tags: Mapped[str] = mapped_column(String(length=200), nullable=False)
	count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

	Index('marseys_idx2', author_id)
	Index('marseys_idx3', count.desc())
	Index('marseys_idx', name)

	def __repr__(self):
		return f"<{self.__class__.__name__}(name={self.name})>"
