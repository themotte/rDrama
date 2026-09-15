from dataclasses import dataclass

from sqlalchemy.sql.schema import Column, ForeignKey, Index
from sqlalchemy.sql.sqltypes import Integer, String
from sqlalchemy.orm import relationship
from files.classes.base import Base
from files.helpers.lazy import lazy
from files.helpers.config.const import *
from files.helpers.assetcache import assetcache_path

@dataclass(frozen=True, kw_only=True, slots=True)
class BadgeDef:
	id: str
	name: str
	description: str

BADGES: list[BadgeDef] = [
	BadgeDef(
		id="unknown",
		name="Unknown Badge",
		description="Please report this if you see it! :x"
	),
	BadgeDef(
		id="verified_email",
		name="Verified Email",
		description="Verified Email"
	),
]

BADGES_DICT: dict[str, BadgeDef] = {badge.id:badge for badge in BADGES}

class Badge(Base):
	__tablename__ = "badges"

	user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
	badge_id = Column(String, nullable=False)
	description = Column(String)
	url = Column(String)

	Index('badges_badge_id_idx', badge_id)

	user = relationship("User", viewonly=True)
	
	@property
	def badge(self) -> BadgeDef:
		return BADGES_DICT.get(self.badge_id, BADGES_DICT['unknown'])

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
