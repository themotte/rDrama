from sqlalchemy import *
from files.__main__ import Base
from files.helpers.lazy import lazy
from os import environ

SITE_NAME = environ.get("SITE_NAME", '').strip()

class Sub(Base):

	__tablename__ = "subs"
	name = Column(String, primary_key=True)
	sidebar = Column(String)
	sidebar_html = Column(String)
	sidebarurl = Column(String)
	bannerurl = Column(String)

	def __repr__(self):
		return f"<Sub(name={self.name})>"

	@property
	@lazy
	def sidebar_url(self):
		if self.sidebarurl: return self.sidebarurl
		return f'/static/assets/images/{SITE_NAME}/sidebar.webp?a=1039'

	@property
	@lazy
	def banner_url(self):
		if self.bannerurl: return self.bannerurl
		return f'/static/assets/images/{SITE_NAME}/banner.webp?a=1039'