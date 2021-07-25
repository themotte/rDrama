from flask import *
from sqlalchemy import *
from sqlalchemy.orm import relationship, lazyload

from .mix_ins import Stndrd
from .submission import Submission
from .comment import Comment
from drama.__main__ import Base


class OauthApp(Base, Stndrd):

	__tablename__ = "oauth_apps"

	id = Column(Integer, primary_key=True)
	client_id = Column(String(64))
	client_secret = Column(String(128))
	app_name = Column(String(50))
	redirect_uri = Column(String(4096))
	author_id = Column(Integer, ForeignKey("users.id"))
	is_banned = Column(Boolean, default=False)
	description = Column(String(256))

	author = relationship("User")

	def __repr__(self):
		return f"<OauthApp(id={self.id})>"

	@property
	def permalink(self):

		return f"/admin/app/{self.base36id}"

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
	oauth_code = Column(String(128))
	user_id = Column(Integer, ForeignKey("users.id"))
	scope_identity = Column(Boolean, default=False)
	scope_create = Column(Boolean, default=False)
	scope_read = Column(Boolean, default=False)
	scope_update = Column(Boolean, default=False)
	scope_delete = Column(Boolean, default=False)
	scope_vote = Column(Boolean, default=False)
	access_token = Column(String(128))
	refresh_token = Column(String(128))
	access_token_expire_utc = Column(Integer)

	user = relationship("User", lazy="joined")
	application = relationship("OauthApp", lazy="joined")

	@property
	def scopelist(self):

		output = ""
		output += "identity," if self.scope_identity else ""
		output += "create," if self.scope_create else ""
		output += "read," if self.scope_read else ""
		output += "update," if self.scope_update else ""
		output += "delete," if self.scope_delete else ""
		output += "vote," if self.scope_vote else ""

		output = output.rstrip(',')

		return output
