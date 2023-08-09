import time

from sqlalchemy import *
from sqlalchemy.orm import Mapped, mapped_column, relationship

from files.classes.base import Base
from files.helpers.lazy import lazy
from files.helpers.time import format_age


class ViewerRelationship(Base):
	__tablename__ = "viewers"

	user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), primary_key=True)
	viewer_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), primary_key=True)
	last_view_utc: Mapped[int] = mapped_column(Integer, nullable=False)

	Index('fki_view_viewer_fkey', viewer_id)

	viewer = relationship("User", primaryjoin="ViewerRelationship.viewer_id == User.id", viewonly=True)

	def __init__(self, **kwargs):
		if 'last_view_utc' not in kwargs:
			kwargs['last_view_utc'] = int(time.time())

		super().__init__(**kwargs)

	@property
	@lazy
	def last_view_since(self):
		return int(time.time()) - self.last_view_utc

	@property
	@lazy
	def last_view_string(self):
		return format_age(self.last_view_utc)
