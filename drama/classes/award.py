#import requests
#from os import environ
from sqlalchemy import *
from sqlalchemy.orm import relationship
#from .mix_ins import *
from drama.__main__ import Base, app

AWARDS = {
	"ban": {
		"title": "1-Day Ban",
		"description": "Ban the author for a day.",
		"icon": "fas fa-gavel",
		"color": "text-danger"
	},
	"shit": {
		"title": "Literal Shitpost",
		"description": "Let OP know how much their post sucks ass.",
		"icon": "fas fa-poop",
		"color": "text-black-50"
	}
}


class AwardRelationship(Base):

	__tablename__ = "award_relationships"

	id = Column(Integer, primary_key=True)

	user_id = Column(Integer, ForeignKey("users.id"))
	submission_id = Column(Integer, ForeignKey("submissions.id"))
	comment_id = Column(Integer, ForeignKey("comments.id"))
	kind = Column(String(20))

	user = relationship("User", primaryjoin="AwardRelationship.user_id==User.id", lazy="joined")
	post = relationship(
		"Submission",
		primaryjoin="AwardRelationship.submission_id==Submission.id",
		lazy="joined"
	)
	comment = relationship(
		"Comment",
		primaryjoin="AwardRelationship.comment_id==Comment.id",
		lazy="joined"
	)

	@property
	def type(self):
		return AWARDS[self.kind]
