from sqlalchemy import *
from drama.__main__ import Base

reasons = {
	1: "URL shorteners are not allowed.",
	3: "Piracy is not allowed.",
	4: "Sites hosting digitally malicious content are not allowed.",
	5: "Spam",
	6: "Doxxing is not allowed.",
	7: "Sexualizing minors is strictly prohibited."
}


class BannedDomain(Base):

	__tablename__ = "banneddomains"
	id = Column(Integer, primary_key=True)
	domain = Column(String)
	reason = Column(Integer, default=0)

	@property
	def reason_text(self): return reasons.get(self.reason)	


class BadLink(Base):

	__tablename__ = "badlinks"
	id = Column(Integer, primary_key=True)
	reason = Column(Integer)
	link = Column(String(512))
	autoban = Column(Boolean, default=False)

	@property
	def reason_text(self): return reasons.get(self.reason)