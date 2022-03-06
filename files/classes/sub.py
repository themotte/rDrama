from sqlalchemy import *
from sqlalchemy.orm import relationship
from files.__main__ import Base
from files.helpers.lazy import lazy
from os import environ
from .sub_subscription import *

SITE_NAME = environ.get("SITE_NAME", '').strip()
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

	subscriptions = relationship("SubSubscription", lazy="dynamic", primaryjoin="SubSubscription.sub==Sub.name", viewonly=True)

	def __repr__(self):
		return f"<Sub(name={self.name})>"

	@property
	@lazy
	def sidebar_url(self):
		if self.sidebarurl: return SITE_FULL + self.sidebarurl
		return f'{SITE_FULL}/static/assets/images/{SITE_NAME}/sidebar.webp?v=1041'

	@property
	@lazy
	def banner_url(self):
		if self.bannerurl: return SITE_FULL + self.bannerurl
		return f'{SITE_FULL}/static/assets/images/{SITE_NAME}/banner.webp?v=1042'

	@property
	@lazy
	def subscription_num(self):
		return self.subscriptions.count()