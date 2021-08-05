from flask import *
from sqlalchemy import *
from sqlalchemy.orm import relationship, lazyload

from .mix_ins import Stndrd
from .submission import Submission
from .comment import Comment
from files.__main__ import Base

class OauthApp(Base, Stndrd):

	__tablename__ = "oauth_apps"

	id = Column(Integer, primary_key=True)
	client_id = Column(String(64))
	app_name = Column(String(50))
	redirect_uri = Column(String(4096))
	description = Column(String(256))
	author_id = Column(Integer, ForeignKey("users.id"))
	author = relationship("User")

	def __repr__(self): return f"<OauthApp(id={self.id})>"

	@property
	def permalink(self): return f"/admin/app/{self.id}"


	def idlist(self, page=1, **kwargs):

		posts = g.db.query(Submission.id).options(lazyload('*')).filter_by(app_id=self.id)
		
		posts=posts.order_by(Submission.created_utc.desc())

		posts=posts.offset(100*(page-1)).limit(101)

		return [x[0] for x in posts.all()]

	def comments_idlist(self, page=1, **kwargs):

		posts = g.db.query(Comment.id).options(lazyload('*')).filter_by(app_id=self.id)
		
		posts=posts.order_by(Comment.created_utc.desc())

		posts=posts.offset(100*(page-1)).limit(101)

		return [x[0] for x in posts.all()]

class ClientAuth(Base, Stndrd):

	__tablename__ = "client_auths"

	id = Column(Integer, primary_key=True)
	oauth_client = Column(Integer, ForeignKey("oauth_apps.id"))
	access_token = Column(String(128))
	user_id = Column(Integer, ForeignKey("users.id"))
	user = relationship("User", lazy="joined")
	application = relationship("OauthApp", lazy="joined")