from sqlalchemy import *
from files.__main__ import Base

class BannedDomain(Base):

	__tablename__ = "banneddomains"
	domain = Column(String, primary_key=True)
	reason = Column(String, nullable=False)
	Index(
		'domains_domain_trgm_idx',
		domain,
		postgresql_using='gin',
		postgresql_ops={'description':'gin_trgm_ops'}
	)
