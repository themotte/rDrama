import enum

from flask import g
from sqlalchemy import *
from sqlalchemy.orm import relationship
from .submission import Submission
from .comment import Comment
from files.classes.base import Base
from files.helpers.lazy import lazy
from files.helpers.config.const import *

class OauthAppState(enum.StrEnum):
	PENDING = "pending"  # requested, awaiting an admin's approval
	APPROVED = "approved"  # has a client id: users can authorize it
	REVOKED = "revoked"  # withdrawn, kept only because its tokens made posts or comments


class OauthApp(Base):

	__tablename__ = "oauth_apps"
	__table_args__ = (
		UniqueConstraint('client_id', name='unique_id'),
		CheckConstraint('revoked_utc IS NULL OR client_id IS NULL', name='oauth_apps_revoked_have_no_client_id'),
	)

	id = Column(Integer, primary_key=True)
	client_id = Column(String(length=64))
	app_name = Column(String(length=50), nullable=False)
	redirect_uri = Column(String(length=4096), nullable=False)
	description = Column(String(length=256), nullable=False)
	author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
	revoked_utc = Column(DateTime(timezone=True))

	author = relationship("User", viewonly=True)

	def __repr__(self): 
		return f"<{self.__class__.__name__}(id={self.id})>"

	@property
	def state(self) -> OauthAppState:
		if self.revoked_utc: return OauthAppState.REVOKED
		return OauthAppState.APPROVED if self.client_id else OauthAppState.PENDING

	@property
	@lazy
	def permalink(self): return f"/admin/app/{self.id}"

	def idlist(self, v, page=1):
		posts = g.db.query(Submission.id).filter(Submission.app_id == self.id, Submission.shadowban_shown_sql(v))
		posts=posts.order_by(Submission.created_utc.desc(), Submission.id.desc())
		posts=posts.offset(100*(page-1)).limit(101)
		return [x[0] for x in posts.all()]

	def comments_idlist(self, v, page=1):
		posts = g.db.query(Comment.id).filter(Comment.app_id == self.id, Comment.shadowban_shown_sql(v))
		posts=posts.order_by(Comment.created_utc.desc(), Comment.id.desc())
		posts=posts.offset(100*(page-1)).limit(101)
		return [x[0] for x in posts.all()]


class ClientAuth(Base):
	__tablename__ = "client_auths"
	__table_args__ = (
		UniqueConstraint('access_token', name='unique_access'),
	)

	user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
	oauth_client = Column(Integer, ForeignKey("oauth_apps.id"), primary_key=True)
	access_token = Column(String(128), nullable=False)
	
	user = relationship("User", viewonly=True)
	application = relationship("OauthApp", viewonly=True)
