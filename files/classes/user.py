from __future__ import annotations

import enum
import time
from datetime import datetime
from typing import TYPE_CHECKING, Union

import pyotp
from flask import g, session
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import aliased, declared_attr, deferred, relationship

from files.classes.alts import Alt
from files.classes.base import CreatedBase
from files.classes.chat_message import ChatMessage
from files.classes.clients import *  # note: imports Comment and Submission
from files.classes.follows import Follow
from files.classes.mod_logs import ModAction
from files.classes.notifications import Notification
from files.classes.saves import CommentSaveRelationship, SaveRelationship
from files.classes.subscriptions import Subscription
from files.classes.userblock import UserBlock
from files.classes.visstate import StateMod
from files.helpers.assetcache import ASSET_URL, assetcache_path
from files.helpers.config.const import *
from files.helpers.config.environment import (CARD_VIEW, DEFAULT_COLOR,
                                              SITE_FULL, SITE_ID)
from files.helpers.security import *

if TYPE_CHECKING:
	from files.classes.cron.submission import ScheduledSubmissionTask

defaulttheme = "TheMotte"

class FilterBehavior(enum.Enum):
    AUTOMATIC = 0
    UNFILTERED = 1
    FILTERED = 2

class User(CreatedBase):
	__tablename__ = "users"
	__table_args__ = (
		UniqueConstraint('bannerurl', name='one_banner'),
		UniqueConstraint('id', name='uid_unique'),
		UniqueConstraint('original_username', name='users_original_username_key'),
		UniqueConstraint('username', name='users_username_key'),
	)
	id = Column(Integer, primary_key=True)
	username = Column(String(length=255), nullable=False)
	namecolor = Column(String(length=6), default=DEFAULT_COLOR, nullable=False)
	customtitle = Column(String)
	customtitleplain = deferred(Column(String))
	titlecolor = Column(String(length=6), default=DEFAULT_COLOR, nullable=False)
	theme = Column(String, default=defaulttheme, nullable=False)
	themecolor = Column(String, default=DEFAULT_COLOR, nullable=False)
	cardview = Column(Boolean, default=CARD_VIEW, nullable=False)
	highres = Column(String)
	profileurl = Column(String)
	bannerurl = Column(String)
	verified = Column(String)
	verifiedcolor = Column(String)
	email = deferred(Column(String))
	css = deferred(Column(String(CSS_LENGTH_MAXIMUM)))
	profilecss = deferred(Column(String(CSS_LENGTH_MAXIMUM)))
	passhash = deferred(Column(String, nullable=False))
	post_count = Column(Integer, default=0, nullable=False)
	comment_count = Column(Integer, default=0, nullable=False)
	account_admin_level = Column('admin_level', Integer, default=0, nullable=False)
	changelogsub = Column(Boolean, default=False, nullable=False)
	is_activated = Column(Boolean, default=False, nullable=False)
	shadowbanned = Column(String)
	over_18 = Column(Boolean, default=False, nullable=False)
	hidevotedon = Column(Boolean, default=False, nullable=False)
	highlightcomments = Column(Boolean, default=True, nullable=False)
	flairchanged = Column(Integer)
	newtab = Column(Boolean, default=False, nullable=False)
	newtabexternal = Column(Boolean, default=True, nullable=False)
	frontsize = Column(Integer, default=25, nullable=False)
	bio = deferred(Column(String))
	bio_html = Column(String)
	friends = deferred(Column(String))
	friends_html = deferred(Column(String))
	is_banned = Column(Integer, default=0, nullable=False)
	unban_utc = Column(Integer, default=0, nullable=False)
	ban_reason = deferred(Column(String))
	login_nonce = Column(Integer, default=0, nullable=False)
	reserved = deferred(Column(String))
	truescore = Column(Integer, default=0, nullable=False)
	mfa_secret = deferred(Column(String))
	is_private = Column(Boolean, default=False, nullable=False)
	stored_subscriber_count = Column(Integer, default=0, nullable=False)
	stored_following_count = Column(Integer, default=0, nullable=False)
	defaultsortingcomments = Column(String, default="new", nullable=False)
	defaultsorting = Column(String, default="new", nullable=False)
	is_nofollow = Column(Boolean, default=False, nullable=False)
	custom_filter_list = Column(String)
	ban_evade = Column(Integer, default=0, nullable=False)
	original_username = deferred(Column(String))
	referred_by = Column(Integer, ForeignKey("users.id"))
	volunteer_last_started_utc = Column(DateTime, nullable=True)
	volunteer_janitor_correctness = Column(Float, default=0, nullable=False)

	chat_authorized = Column(Boolean, default=False, nullable=False)
	chat_lastseen = Column(DateTime(timezone=True), default=datetime(1970, 1, 1), nullable=False)

	filter_behavior = Column(Enum(FilterBehavior), default=FilterBehavior.AUTOMATIC, nullable=False)

	Index(
		'users_original_username_trgm_idx',
		original_username,
		postgresql_using='gin',
		postgresql_ops={'description':'gin_trgm_ops'}
	)
	Index(
		'users_username_trgm_idx',
		username,
		postgresql_using='gin',
		postgresql_ops={'description':'gin_trgm_ops'}
	)

	Index('fki_user_referrer_fkey', referred_by)
	Index('user_banned_idx', is_banned)
	Index('user_private_idx', is_private)

	@declared_attr
	def users_created_utc_index(self):
		return Index('users_created_utc_index', self.created_utc)

	Index('users_subs_idx', stored_subscriber_count)
	Index('users_unbanutc_idx', unban_utc.desc())

	Index('chat_auth_index', chat_authorized)

	subscriptions = relationship("Subscription", viewonly=True)
	following = relationship("Follow", primaryjoin="Follow.user_id==User.id", viewonly=True)
	followers = relationship("Follow", primaryjoin="Follow.target_id==User.id", viewonly=True)
	blocking = relationship("UserBlock", lazy="dynamic", primaryjoin="User.id==UserBlock.user_id", viewonly=True)
	blocked = relationship("UserBlock", lazy="dynamic", primaryjoin="User.id==UserBlock.target_id", viewonly=True)
	authorizations = relationship("ClientAuth", viewonly=True)
	referrals = relationship("User", viewonly=True)
	notes = relationship("UserNote", foreign_keys='UserNote.reference_user', back_populates="user")

	@hybrid_property
	def admin_level(self) -> int:
		'''The admin level to act with: the account's own (account_admin_level), except 0 for the user an API token authenticated, since such requests act with no admin powers. The session holds one object per row, so that user reads 0 wherever the request loads them, as well as the viewer.'''
		return 0 if self.__dict__.get("client") else self.account_admin_level

	@admin_level.inplace.setter
	def _admin_level_setter(self, value:int) -> None:
		self.account_admin_level = value

	@admin_level.inplace.expression
	@classmethod
	def _admin_level_expression(cls):
		return cls.account_admin_level

	def __init__(self, **kwargs):
		if "password" in kwargs:
			kwargs["passhash"] = self.hash_password(kwargs["password"])
			kwargs.pop("password")
		super().__init__(**kwargs)

	def can_manage_reports(self):
		return self.admin_level > 1

	@property
	@lazy
	def can_send_messages(self):
		# Users can't send messages until they've had a post or comment approved
		return self.admin_level > 0 \
			or self.post_count > 0 \
			or self.comment_count > 0
	
	@property
	@lazy
	def can_access_chat(self):
		if self.is_suspended_permanently:
			return False
		if self.admin_level >= PERMS['CHAT_FULL_CONTROL']:
			return True
		if self.chat_authorized:
			return True
		return False
	
	@property
	@lazy
	def unread_chat_messages_count(self):
		if not self.can_access_chat:
			return 0

		# Query for all chat messages that are newer than the user's last seen timestamp
		unread_messages_count = g.db.query(ChatMessage)\
			.filter(ChatMessage.created_datetimez > self.chat_lastseen)\
			.count()

		return unread_messages_count
	
	@property
	def age_days(self):
		return (datetime.now() - datetime.fromtimestamp(self.created_utc)).days

	@property
	def should_comments_be_filtered(self):
		from files.__main__ import app  # avoiding import loop
		if self.admin_level > 0:
			return False
		if self.filter_behavior != FilterBehavior.AUTOMATIC:
			return self.filter_behavior == FilterBehavior.FILTERED
		
		# Automatic path here
		# TODO: move settings out of app.config
		site_settings = app.config['SETTINGS']
		min_comments = site_settings.get('FilterCommentsMinComments', 0)
		min_karma = site_settings.get('FilterCommentsMinKarma', 0)
		min_age = site_settings.get('FilterCommentsMinAgeDays', 0)
		return self.comment_count < min_comments \
			or self.age_days < min_age \
			or self.truescore < min_karma


	def can_change_user_privacy(self, v: "User") -> bool:
		from files.__main__ import app  # avoiding import loop
		if v.admin_level >= PERMS['USER_SET_PROFILE_PRIVACY']: return True
		if self.id != v.id: return False # non-admin changing someone else's things, hmm...

		# TODO: move settings out of app.config
		site_settings = app.config['SETTINGS']
		min_comments: int = site_settings.get('min_comments_private_profile', 0)
		min_truescore: int = site_settings.get('min_truescore_private_profile', 0)
		min_age_days: int = site_settings.get('min_age_days_private_profile', 0)
		user_age_days: int = self.age_timedelta.days

		return (
			self.comment_count >= min_comments
			and self.truescore >= min_truescore
			and user_age_days  >= min_age_days)
	

	@property
	@lazy
	def csslazy(self):
		return self.css

	@property
	def referral_count(self):
		return len(self.referrals)

	def is_blocking(self, target):
		return g.db.query(UserBlock).filter_by(user_id=self.id, target_id=target.id).one_or_none()

	@lazy
	def any_block_exists(self, other):
		return g.db.query(UserBlock).filter(
			or_(and_(UserBlock.user_id == self.id, UserBlock.target_id == other.id), and_(
				UserBlock.user_id == other.id, UserBlock.target_id == self.id))).first()

	def validate_2fa(self, token):
		if not self.mfa_secret or not token: return False
		x = pyotp.TOTP(self.mfa_secret)
		return x.verify(token.strip(), valid_window=1)

	@property
	@lazy
	def ban_reason_link(self):
		if self.ban_reason:
			if self.ban_reason.startswith("/post/"): return self.ban_reason.split(None, 1)[0]
			if self.ban_reason.startswith("/comment/"): return self.ban_reason.split(None, 1)[0] + "?context=8#context"

	@property
	@lazy
	def alts_unique(self):
		alts = []
		for u in self.alts:
			if u not in alts: alts.append(u)
		return alts

	@property
	@lazy
	def follow_count(self):
		return self.stored_following_count

	@property
	@lazy
	def bio_html_eager(self):
		if self.bio_html == None: return ''
		return self.bio_html.replace('data-src', 'src').replace('src="/assets/images/loading.webp"', '')

	@property
	@lazy
	def fullname(self):
		return f"user_{self.id}"

	@property
	@lazy
	def banned_by(self):
		if not self.is_suspended: return None
		return g.db.query(User).filter_by(id=self.is_banned).one_or_none()

	def sign_out_everywhere(self):
		'''Ends every session of the account (each remembers the nonce it logged in with; a request keeps its own by storing the new nonce in it) and every API token it holds.'''
		self.login_nonce += 1
		g.db.query(ClientAuth).filter_by(user_id=self.id).delete()

	def hash_password(self, password):
		# Use faster hashing with fewer iterations during tests
		# PBKDF2 default is 260000 iterations, we use 1000 for tests
		import os
		if os.environ.get('RDRAMA_TESTING') == '1':
			# Fast hashing for tests (~2ms instead of ~390ms)
			method = 'pbkdf2:sha512:1000'
		else:
			# Secure hashing for production (default 260000 iterations)
			method = 'pbkdf2:sha512'
		return generate_password_hash(password, method=method, salt_length=8)

	def verifyPass(self, password):
		return check_password_hash(self.passhash, password)

	@property
	@lazy
	def formkey(self):
		msg = f"{session['session_id']}+{self.id}+{self.login_nonce}"

		return generate_hash(msg)

	def validate_formkey(self, formkey):
		if not formkey or not isinstance(formkey, str): return False
		return validate_hash(f"{session['session_id']}+{self.id}+{self.login_nonce}", formkey)

	@property
	@lazy
	def url(self):
		return f"/@{self.username}"

	def __repr__(self):
		# Memoized pages key on repr(v), and an API client sees less than the same user in the browser
		client = ", api" if self.__dict__.get("client") else ""
		return f"<{self.__class__.__name__}(id={self.id}{client})>"

	@property
	@lazy
	def unban_string(self):
		if self.unban_utc == 0:
			return "permanently banned"

		wait = self.unban_utc - int(time.time())

		if wait < 60:
			text = f"{wait}s"
		else:
			days = wait//(24*60*60)
			wait -= days*24*60*60

			hours = wait//(60*60)
			wait -= hours*60*60

			mins = wait//60

			text = f"{days}d {hours:02d}h {mins:02d}m"

		return f"Unban in {text}"


	@property
	@lazy
	def notifications_count(self):
		'''The user's unread notifications that the notification pages show, of both kinds.'''
		from files.helpers.notifications import shown_notifications
		return shown_notifications(g.db.query(Notification.user_id).join(Comment), self).filter(Notification.read == False).count()

	@property
	@lazy
	def post_notifications_count(self):
		return g.db.query(Notification.user_id).join(Comment).filter(Notification.user_id == self.id, Notification.read == False, Comment.author_id == AUTOJANNY_ID).count()

	@property
	@lazy
	def normal_count(self):
		return self.notifications_count - self.post_notifications_count

	@property
	@lazy
	def do_posts(self):
		return self.post_notifications_count and self.notifications_count == self.post_notifications_count

	@property
	@lazy
	def alts(self):
		subq = g.db.query(Alt).filter(
			or_(
				Alt.user1 == self.id,
				Alt.user2 == self.id
			)
		).subquery()

		data = g.db.query(
			User,
			aliased(Alt, alias=subq)
		).join(
			subq,
			or_(
				subq.c.user1 == User.id,
				subq.c.user2 == User.id
			)
		).filter(
			User.id != self.id
		).order_by(User.username).all()

		data = [x for x in data]
		output = []
		for x in data:
			user = x[0]
			user._is_manual = x[1].is_manual
			output.append(user)

		return output

	def has_follower(self, user):
		return g.db.query(Follow).filter_by(target_id=self.id, user_id=user.id).one_or_none()

	@property
	@lazy
	def banner_url(self):
		if self.bannerurl:
			return self.bannerurl
		return assetcache_path(f'images/{SITE_ID}/site_preview.webp')

	@property
	@lazy
	def profile_url(self):
		if self.profileurl:
			# Stored addresses of site files (the default picture) carry no version
			if self.profileurl.startswith(ASSET_URL) and '?' not in self.profileurl:
				return SITE_FULL + assetcache_path(self.profileurl[len(ASSET_URL):])
			if self.profileurl.startswith('/'):
				return SITE_FULL + self.profileurl
			return self.profileurl
		return assetcache_path('images/default-profile-pic.webp')

	@lazy
	def json_popover(self, v):
		data = {'username': self.username,
				'url': self.url,
				'id': self.id,
				'profile_url': self.profile_url,
				'bannerurl': self.banner_url,
				'bio_html': self.bio_html_eager,
				'post_count': self.post_count if self.shows_activity_to(v) else 0,
				'comment_count': self.comment_count if self.shows_activity_to(v) else 0,
				}

		return data

	@lazy
	def json_notes(self, v):
		data = {'username': self.username,
				'url': self.url,
				'id': self.id,
				'notes': [x.json() for x in sorted(self.notes, key=lambda x: x.created_utc)]
				}

		return data

	@property
	@lazy
	def json_raw(self):
		data = {'username': self.username,
				'url': self.url,
				'is_banned': bool(self.is_banned),
				'created_utc': self.created_utc,
				'id': self.id,
				'is_private': self.is_private,
				'profile_url': self.profile_url,
				'bannerurl': self.banner_url,
				'bio': self.bio,
				'bio_html': self.bio_html_eager,
				'flair': self.customtitle
				}

		return data

	@property
	@lazy
	def json_core(self):
		if self.is_suspended:
			return {'username': self.username,
					'url': self.url,
					'is_banned': True,
					'is_permanent_ban': not bool(self.unban_utc),
					'ban_reason': self.ban_reason,
					'id': self.id
					}
		return self.json_raw

	@property
	@lazy
	def json(self):
		return {**self.json_core, 'post_count': self.post_count, 'comment_count': self.comment_count}

	def json_for(self, v:"User | None") -> dict:
		'''The user's JSON as `v` may see it: the post and comment counts read 0 unless the user shows their activity to `v`.'''
		if self.shows_activity_to(v): return self.json
		return {**self.json, 'post_count': 0, 'comment_count': 0}


	def ban(self, admin=None, reason=None, until=0):
		'''Suspends the account until the epoch time `until`, or for good if it's 0.'''
		self.unban_utc = until
		self.is_banned = admin.id if admin else AUTOJANNY_ID
		self.ban_reason = reason or None
		g.db.add(self)

	@property
	def is_suspended(self):
		return (self.is_banned and (self.unban_utc == 0 or self.unban_utc > time.time()))

	@property
	def is_suspended_permanently(self):
		return (self.is_banned and self.unban_utc == 0)

	@hybrid_property
	def reports_count(self) -> bool:
		'''Whether the user's reports bring items to the moderators: not those of permanently suspended or shadowbanned users.'''
		return not (self.is_suspended_permanently or self.shadowbanned)

	@reports_count.expression
	def reports_count(cls):
		return and_(cls.shadowbanned == None, not_(and_(cls.is_banned != 0, cls.unban_utc == 0)))

	@property
	@lazy
	def applications(self):
		return g.db.query(OauthApp).filter_by(author_id=self.id).order_by(OauthApp.id)

	@lazy
	def subscribed_idlist(self, page=1):
		posts = g.db.query(Subscription.submission_id).filter_by(user_id=self.id).all()
		return [x[0] for x in posts]
	
	@property
	@lazy
	def all_userblocks(self):
		''' User blocks by and targeting this user '''
		return [x[0] for x in g.db.query(UserBlock.target_id).filter(or_(UserBlock.user_id == self.id, UserBlock.target_id == self.id)).all()]

	@property
	@lazy
	def userblocks(self):
		''' User blocks by this user '''
		return [x[0] for x in g.db.query(UserBlock.target_id).filter_by(user_id=self.id).all()]

	@lazy
	def saved_idlist(self) -> list[int]:
		'''Ids of the posts this user saved that their saved list shows, newest first.'''
		saved = [x[0] for x in g.db.query(SaveRelationship.submission_id).filter_by(user_id=self.id).all()]
		posts = g.db.query(Submission.id).filter(Submission.id.in_(saved), Submission.state_mod == StateMod.VISIBLE, Submission.state_user_deleted_utc == None)

		if self.admin_level < 2:
			posts = posts.filter(Submission.author_id.notin_(self.userblocks))

		posts = posts.filter(Submission.shadowban_shown_sql(self))

		return [x[0] for x in posts.order_by(Submission.created_utc.desc(), Submission.id.desc()).all()]

	@lazy
	def saved_comment_idlist(self) -> list[int]:
		'''Ids of the comments this user saved that their saved list shows, newest first.'''
		saved = [x[0] for x in g.db.query(CommentSaveRelationship.comment_id).filter_by(user_id=self.id).all()]
		comments = g.db.query(Comment.id).join(Submission, Submission.id == Comment.parent_submission).filter(Comment.id.in_(saved), Comment.state_mod == StateMod.VISIBLE, Comment.state_user_deleted_utc == None)

		if self.admin_level < PERMS['POST_COMMENT_MODERATION']:
			comments = comments.filter(or_(Submission.private == False, Submission.author_id == self.id))

		if self.admin_level < 2:
			comments = comments.filter(Comment.author_id.notin_(self.userblocks))

		comments = comments.filter(Comment.shadowban_shown_sql(self))

		return [x[0] for x in comments.order_by(Comment.created_utc.desc(), Comment.id.desc()).all()]

	@property
	@lazy
	def saved_count(self):
		return len(self.saved_idlist())

	@property
	@lazy
	def saved_comment_count(self):
		return len(self.saved_comment_idlist())

	@property
	@lazy
	def filter_words(self):
		l = [i.strip() for i in self.custom_filter_list.split('\n')] if self.custom_filter_list else []
		l = [i for i in l if i]
		return l
	
	# Permissions

	def can_edit(self, target:Union[Submission, ScheduledSubmissionTask]):
		if isinstance(target, Submission):
			if self.id == target.author_id: return True
			return self.admin_level >= PERMS['POST_EDITING']
		if target.__class__.__name__ == "ScheduledSubmissionTask": 
			# XXX: avoiding import loop. should be fixed someday.
			return self.admin_level >= PERMS['SCHEDULER_POSTS']

	def shows_activity_to(self, v:"User | None") -> bool:
		'''Whether `v` may see this user's posts and comments, and how many there are: everyone may, unless the user is shadowbanned or private, when only they and admins may.'''
		if v and v.id == self.id: return True
		if self.shadowbanned and not (v and v.admin_level >= PERMS['USER_SHADOWBAN']): return False
		if self.is_private and not (v and v.admin_level >= PERMS['USER_SET_PROFILE_PRIVACY']): return False
		return True

