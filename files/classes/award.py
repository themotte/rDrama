from sqlalchemy import *
from sqlalchemy.orm import relationship
from files.classes.base import Base
from files.helpers.config.const import AWARDS
from files.helpers.lazy import lazy

class AwardRelationship(Base):

	__tablename__ = "award_relationships"
	__table_args__ = (
		UniqueConstraint('user_id', 'submission_id', 'comment_id', name='award_constraint'),
	)

	id = Column(Integer, primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
	submission_id = Column(Integer, ForeignKey("submissions.id"))
	comment_id = Column(Integer, ForeignKey("comments.id"))
	kind = Column(String, nullable=False)

	user = relationship("User", primaryjoin="AwardRelationship.user_id==User.id", viewonly=True)
	post = relationship("Submission", primaryjoin="AwardRelationship.submission_id==Submission.id", viewonly=True)
	comment = relationship("Comment", primaryjoin="AwardRelationship.comment_id==Comment.id", viewonly=True)

	Index('award_user_idx', user_id)
	Index('award_post_idx', submission_id)
	Index('award_comment_idx', comment_id)


	@property
	@lazy
	def type(self):
		return AWARDS[self.kind]

	@property
	@lazy
	def title(self):
		return self.type['title']

	@property
	@lazy
	def class_list(self):
		return self.type['icon']+' '+self.type['color']
