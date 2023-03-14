from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import Column, Index
from sqlalchemy.sql.sqltypes import String

from files.classes.base import Base
from files.helpers.config.environment import SITE_FULL
from files.helpers.lazy import lazy


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
		return f"<{self.__class__.__name__}(name={self.name})>"

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
