from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.sqltypes import String
from sqlalchemy.schema import Index
from files.classes.base import Base

class BannedDomain(Base):
	__tablename__ = "banneddomains"
	domain: Mapped[str] = mapped_column(String, primary_key=True)
	reason: Mapped[str | None] = mapped_column(String, nullable=False)
	Index(
		'domains_domain_trgm_idx',
		domain,
		postgresql_using='gin',
		postgresql_ops={'description':'gin_trgm_ops'}
	)
