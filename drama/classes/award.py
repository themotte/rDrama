#import requests
#from os import environ
from sqlalchemy import *
from sqlalchemy.orm import relationship
#from .mix_ins import *
from drama.__main__ import Base, app


class AwardRelationship(Base):

	__tablename__ = "award_relationships"

	id = Column(Integer, primary_key=True)

	user_id = Column(Integer, ForeignKey("users.id"))
	submission_id = Column(Integer, ForeignKey("submissions.id"), default=None)
	comment_id = Column(Integer, ForeignKey("comments.id"), default=None)

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
