from sqlalchemy import *
from sqlalchemy.orm import relationship
from files.__main__ import Base, app
from os import environ
from files.helpers.lazy import lazy
from files.helpers.const import BADGES
from datetime import datetime

site_name = environ.get("SITE_NAME").strip()

class Badge(Base):

	__tablename__ = "badges"

	id = Column(Integer, primary_key=True)

	user_id = Column(Integer, ForeignKey('users.id'))
	badge_id = Column(Integer)
	description = Column(String)
	url = Column(String)
	user = relationship("User", viewonly=True)

	def __repr__(self):
		return f"<Badge(user_id={self.user_id}, badge_id={self.badge_id})>"

	@property
	@lazy
	def badge(self):
		return BADGES[self.badge_id]

	@property
	@lazy
	def text(self):
		if self.name == "Agendaposter":
			ti = self.user.agendaposter_expires_utc
			if ti: return self.badge['description'] + " until " + datetime.utcfromtimestamp(ti).strftime('%Y-%m-%d %H:%M:%S')
			else: return self.badge['description'] + " permanently" 
		elif self.description: return self.description
		else: return self.badge['description']

	@property
	@lazy
	def name(self):
		return self.badge['name']

	@property
	@lazy
	def path(self):
		return f"/assets/images/badges/{self.name.replace(' ','%20')}.webp"

	@property
	@lazy
	def json_core(self):

		return {'text': self.text,
				'name': self.name,
				'url': self.url,
				'icon_url':f"https://{app.config['SERVER_NAME']}{self.path}"
				}

	@property
	@lazy
	def json(self):
		return self.json_core
