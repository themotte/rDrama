from sqlalchemy import *
from sqlalchemy.orm import relationship
from files.classes.base import Base
from files.helpers.lazy import lazy
from os import environ
from .sub_block import *

SITE = environ.get("DOMAIN", '').strip()
if SITE == "localhost": SITE_FULL = 'http://' + SITE
else: SITE_FULL = 'https://' + SITE

class Sub(Base):

	__tablename__ = "subs"
	name = Column(String, primary_key=True)
	sidebar = Column(String)
	sidebar_html = Column(String)
	sidebarurl = Column(String)
	bannerurl = Column(String)
	css = Column(String)

	Index('subs_idx', name)

	blocks = relationship("SubBlock", lazy="dynamic", primaryjoin="SubBlock.sub==Sub.name", viewonly=True)


	def __repr__(self):
		return f"<Sub(name={self.name})>"

	@property
	@lazy
	def sidebar_url(self):
		if self.sidebarurl: return SITE_FULL + self.sidebarurl
		return None # Add default sidebar for subs if subs are used again

	@property
	@lazy
	def banner_url(self):
		if self.bannerurl: return SITE_FULL + self.bannerurl
		return None # Add default banner for subs if subs are used again

	@property
	@lazy
	def subscription_num(self):
		return self.subscriptions.count()

	@property
	@lazy
	def block_num(self):
		return self.blocks.count()
