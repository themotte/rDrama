from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import Column, ForeignKey, Index, UniqueConstraint
from sqlalchemy.sql.sqltypes import Integer, String

from files.classes.base import Base
from files.helpers.assetcache import assetcache_path
from files.helpers.lazy import lazy


class BadgeDef(Base):
	__tablename__ = "badge_defs"
	__table_args__ = (
		UniqueConstraint('name', name='badge_def_name_unique'),
	)

	id = Column(Integer, primary_key=True, autoincrement=True)
	name = Column(String, nullable=False)
	description = Column(String)

	def __repr__(self):
		return f"<BadgeDef(id={self.id})>"

class Badge(Base):

	__tablename__ = "badges"

	user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
	badge_id = Column(Integer,  ForeignKey('badge_defs.id'), primary_key=True)
	description = Column(String)
	url = Column(String)

	Index('badges_badge_id_idx', badge_id)

	user = relationship("User", viewonly=True)
	badge = relationship("BadgeDef",
		primaryjoin="foreign(Badge.badge_id) == remote(BadgeDef.id)",
		lazy="joined", innerjoin=True, viewonly=True)

	def __repr__(self):
		return f"<Badge(user_id={self.user_id}, badge_id={self.badge_id})>"

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
