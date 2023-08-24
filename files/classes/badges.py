from sqlalchemy import *
from sqlalchemy.orm import relationship
from files.classes.base import Base
from files.helpers.lazy import lazy
from files.helpers.config.const import *
from sqlalchemy.orm import Mapped, mapped_column, relationship
from files.helpers.assetcache import assetcache_path

class BadgeDef(Base):
	__tablename__ = "badge_defs"
	__table_args__ = (
		UniqueConstraint('name', name='badge_def_name_unique'),
	)

	id = mapped_column(Integer, primary_key=True, autoincrement=True)
	name = mapped_column(String, nullable=False)
	description = mapped_column(String)

	def __repr__(self):
		return f"<{self.__class__.__name__}(id={self.id})>"

class Badge(Base):

	__tablename__ = "badges"

	user_id = mapped_column(Integer, ForeignKey('users.id'), primary_key=True)
	badge_id = mapped_column(Integer,  ForeignKey('badge_defs.id'), primary_key=True)
	description = mapped_column(String)
	url = mapped_column(String)

	Index('badges_badge_id_idx', badge_id)

	user = relationship("User", viewonly=True)
	badge = relationship("BadgeDef",
		primaryjoin="foreign(Badge.badge_id) == remote(BadgeDef.id)",
		lazy="joined", innerjoin=True, viewonly=True)

	def __repr__(self):
		return f"<{self.__class__.__name__}(user_id={self.user_id}, badge_id={self.badge_id})>"

	@property
	@lazy
	def text(self):
		if self.description: text = self.description
		elif self.badge.description: text = self.badge.description
		else: return self.name
		return f'{self.name} - {text}'

	@property
	@lazy
	def name(self):
		return self.badge.name

	@property
	@lazy
	def path(self):
		return assetcache_path(f'images/badges/{self.badge_id}.webp')

	@property
	@lazy
	def json(self):
		return {'text': self.text,
				'name': self.name,
				'url': self.url,
				'icon_url':self.path
				}
