import time
from typing import Union

import pyotp
from flask import g, session
from sqlalchemy.orm import aliased, declared_attr, deferred, relationship

from files.classes.alts import Alt
from files.classes.award import AwardRelationship
from files.classes.badges import Badge
from files.classes.base import CreatedBase
from files.classes.clients import *  # note: imports Comment and Submission
from files.classes.cron.submission import ScheduledSubmissionTask
from files.classes.exiles import *
from files.classes.follows import Follow
from files.classes.mod import Mod
from files.classes.notifications import Notification
from files.classes.saves import CommentSaveRelationship, SaveRelationship
from files.classes.sub_block import SubBlock
from files.classes.subscriptions import Subscription
from files.classes.userblock import UserBlock
from files.helpers.assetcache import assetcache_path
from files.helpers.config.const import *
from files.helpers.config.environment import (CARD_VIEW,
                                              CLUB_TRUESCORE_MINIMUM,
                                              DEFAULT_COLOR,
                                              DEFAULT_TIME_FILTER, SITE_FULL,
                                              SITE_ID)
from files.helpers.security import *

defaulttheme = "TheMotte"

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
	background = Column(String)
	customtitle = Column(String)
	customtitleplain = deferred(Column(String))
	titlecolor = Column(String(length=6), default=DEFAULT_COLOR, nullable=False)
	theme = Column(String, default=defaulttheme, nullable=False)
	themecolor = Column(String, default=DEFAULT_COLOR, nullable=False)
	cardview = Column(Boolean, default=CARD_VIEW, nullable=False)
	highres = Column(String)
	profileurl = Column(String)
	bannerurl = Column(String)
	house = Column(String)
	patron = Column(Integer, default=0, nullable=False)
	patron_utc = Column(Integer, default=0, nullable=False)
	verified = Column(String)
	verifiedcolor = Column(String)
	winnings = Column(Integer, default=0, nullable=False)
	email = deferred(Column(String))
	css = deferred(Column(String(CSS_LENGTH_MAXIMUM)))
	profilecss = deferred(Column(String(CSS_LENGTH_MAXIMUM)))
	passhash = deferred(Column(String, nullable=False))
	post_count = Column(Integer, default=0, nullable=False)
	comment_count = Column(Integer, default=0, nullable=False)
	received_award_count = Column(Integer, default=0, nullable=False)
	admin_level = Column(Integer, default=0, nullable=False)
	coins_spent = Column(Integer, default=0, nullable=False)
	lootboxes_bought = Column(Integer, default=0, nullable=False)
	agendaposter = Column(Integer, default=0, nullable=False)
	changelogsub = Column(Boolean, default=False, nullable=False)
	is_activated = Column(Boolean, default=False, nullable=False)
	shadowbanned = Column(String)
	over_18 = Column(Boolean, default=False, nullable=False)
	hidevotedon = Column(Boolean, default=False, nullable=False)
	highlightcomments = Column(Boolean, default=True, nullable=False)
	slurreplacer = Column(Boolean, default=True, nullable=False)
	flairchanged = Column(Integer)
	newtab = Column(Boolean, default=False, nullable=False)
	newtabexternal = Column(Boolean, default=True, nullable=False)
	reddit = Column(String, default='old.reddit.com', nullable=False)
	nitter = Column(Boolean)
	frontsize = Column(Integer, default=25, nullable=False)
	controversial = Column(Boolean, default=False, nullable=False)
	bio = deferred(Column(String))
	bio_html = Column(String)
	fp = Column(String)
	friends = deferred(Column(String))
	friends_html = deferred(Column(String))
	enemies = deferred(Column(String))
	enemies_html = deferred(Column(String))
	is_banned = Column(Integer, default=0, nullable=False)
	unban_utc = Column(Integer, default=0, nullable=False)
	ban_reason = deferred(Column(String))
	club_allowed = Column(Boolean)
	login_nonce = Column(Integer, default=0, nullable=False)
	reserved = deferred(Column(String))
	coins = Column(Integer, default=0, nullable=False)
	truecoins = Column(Integer, default=0, nullable=False)
	procoins = Column(Integer, default=0, nullable=False)
	mfa_secret = deferred(Column(String))
	is_private = Column(Boolean, default=False, nullable=False)
	stored_subscriber_count = Column(Integer, default=0, nullable=False)
	defaultsortingcomments = Column(String, default="new", nullable=False)
	defaultsorting = Column(String, default="new", nullable=False)
	defaulttime = Column(String, default=DEFAULT_TIME_FILTER, nullable=False)
	is_nofollow = Column(Boolean, default=False, nullable=False)
	custom_filter_list = Column(String)
	ban_evade = Column(Integer, default=0, nullable=False)
	original_username = deferred(Column(String))
	referred_by = Column(Integer, ForeignKey("users.id"))
	subs_created = Column(Integer, default=0, nullable=False)
	volunteer_last_started_utc = Column(DateTime, nullable=True)

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

	badges = relationship("Badge", viewonly=True)
	subscriptions = relationship("Subscription", viewonly=True)
	following = relationship("Follow", primaryjoin="Follow.user_id==User.id", viewonly=True)
	followers = relationship("Follow", primaryjoin="Follow.target_id==User.id", viewonly=True)
	viewers = relationship("ViewerRelationship", primaryjoin="User.id == ViewerRelationship.user_id", viewonly=True)
	blocking = relationship("UserBlock", lazy="dynamic", primaryjoin="User.id==UserBlock.user_id", viewonly=True)
	blocked = relationship("UserBlock", lazy="dynamic", primaryjoin="User.id==UserBlock.target_id", viewonly=True)
	authorizations = relationship("ClientAuth", viewonly=True)
	awards = relationship("AwardRelationship", primaryjoin="User.id==AwardRelationship.user_id", viewonly=True)
	referrals = relationship("User", viewonly=True)
	notes = relationship("UserNote", foreign_keys='UserNote.reference_user', back_populates="user")

	def __init__(self, **kwargs):
		if "password" in kwargs:
			kwargs["passhash"] = self.hash_password(kwargs["password"])
			kwargs.pop("password")
		super().__init__(**kwargs)

	def can_manage_reports(self):
		return self.admin_level > 1

	def should_comments_be_filtered(self):
		from files.__main__ import app  # avoiding import loop
		if self.admin_level > 0:
			return False
		# TODO: move settings out of app.config
		site_settings = app.config['SETTINGS']
		minComments = site_settings.get('FilterCommentsMinComments', 0)
		minKarma = site_settings.get('FilterCommentsMinKarma', 0)
		minAge = site_settings.get('FilterCommentsMinAgeDays', 0)
		accountAgeDays = self.age_timedelta.days
		return self.comment_count < minComments or accountAgeDays < minAge or self.truecoins < minKarma

	@lazy
	def mods(self, sub):
		return self.admin_level == 3 or bool(g.db.query(Mod.user_id).filter_by(user_id=self.id, sub=sub).one_or_none())

	@lazy
	def exiled_from(self, sub):
		return self.admin_level < 2 and bool(g.db.query(Exile.user_id).filter_by(user_id=self.id, sub=sub).one_or_none())

	@property
	@lazy
	def all_blocks(self):
		return [x[0] for x in g.db.query(SubBlock.sub).filter_by(user_id=self.id).all()]

	@lazy
	def blocks(self, sub):
		return g.db.query(SubBlock).filter_by(user_id=self.id, sub=sub).one_or_none()

	@lazy
	def mod_date(self, sub):
		if self.id == OWNER_ID: return 1
		mod = g.db.query(Mod).filter_by(user_id=self.id, sub=sub).one_or_none()
		if not mod: return None
		return mod.created_utc

	@property
	@lazy
	def csslazy(self):
		return self.css

	@property
	@lazy
	def discount(self):
		if self.patron == 1: discount = 0.90
		elif self.patron == 2: discount = 0.85
		elif self.patron == 3: discount = 0.80
		elif self.patron == 4: discount = 0.75
		elif self.patron == 5: discount = 0.70
		elif self.patron == 6: discount = 0.65
		else: discount = 1

		for badge in [69,70,71,72,73]:
			if self.has_badge(badge): discount -= discounts[badge]

		return discount

	@property
	@lazy
	def user_awards(self):
		if not FEATURES['AWARDS']: return []
		return_value = list(AWARDS_ENABLED.values())
		user_awards = g.db.query(AwardRelationship).filter_by(user_id=self.id)
		for val in return_value: val['owned'] = user_awards.filter_by(kind=val['kind'], submission_id=None, comment_id=None).count()
		return return_value

	@property
	def referral_count(self):
		return len(self.referrals)

	def is_blocking(self, target):
		return g.db.query(UserBlock).filter_by(user_id=self.id, target_id=target.id).one_or_none()

	@property
	@lazy
	def paid_dues(self):
		return not self.shadowbanned and not (self.is_banned and not self.unban_utc) and (self.admin_level or self.club_allowed or (self.club_allowed != False and self.truecoins > CLUB_TRUESCORE_MINIMUM))

	@lazy
	def any_block_exists(self, other):

		return g.db.query(UserBlock).filter(
			or_(and_(UserBlock.user_id == self.id, UserBlock.target_id == other.id), and_(
				UserBlock.user_id == other.id, UserBlock.target_id == self.id))).first()

	def validate_2fa(self, token):

		x = pyotp.TOTP(self.mfa_secret)
		return x.verify(token, valid_window=1)

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
	def alts_patron(self):
		for u in self.alts_unique:
			if u.patron: return True
		return False

	@property
	@lazy
	def follow_count(self):
		return g.db.query(Follow.target_id).filter_by(user_id=self.id).count()

	@property
	@lazy
	def bio_html_eager(self):
		if self.bio_html == None: return ''
		return self.bio_html.replace('data-src', 'src').replace('src="/assets/images/loading.webp"', '')

	@property
	@lazy
	def fullname(self):
		return f"t1_{self.id}"

	@property
	@lazy
	def banned_by(self):
		if not self.is_suspended: return None
		return g.db.query(User).filter_by(id=self.is_banned).one_or_none()

	def has_badge(self, badge_id):
		return g.db.query(Badge).filter_by(user_id=self.id, badge_id=badge_id).one_or_none()

	def hash_password(self, password):
		return generate_password_hash(
			password, method='pbkdf2:sha512', salt_length=8)

	def verifyPass(self, password):
		return check_password_hash(self.passhash, password)

	@property
	@lazy
	def formkey(self):
		msg = f"{session['session_id']}+{self.id}+{self.login_nonce}"

		return generate_hash(msg)

	def validate_formkey(self, formkey):
		if not formkey: return False
		return validate_hash(f"{session['session_id']}+{self.id}+{self.login_nonce}", formkey)

	@property
	@lazy
	def url(self):
		return f"/@{self.username}"

	def __repr__(self):
		return f"<{self.__class__.__name__}(id={self.id})>"

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
	def received_awards(self):
		if not FEATURES['AWARDS']: return []
		awards = {}

		posts_idlist = [x[0] for x in g.db.query(Submission.id).filter_by(author_id=self.id).all()]
		comments_idlist = [x[0] for x in g.db.query(Comment.id).filter_by(author_id=self.id).all()]

		post_awards = g.db.query(AwardRelationship).filter(AwardRelationship.submission_id.in_(posts_idlist)).all()
		comment_awards = g.db.query(AwardRelationship).filter(AwardRelationship.comment_id.in_(comments_idlist)).all()

		total_awards = post_awards + comment_awards

		for a in total_awards:
			if a.kind in awards:
				awards[a.kind]['count'] += 1
			else:
				awards[a.kind] = a.type
				awards[a.kind]['count'] = 1

		return sorted(list(awards.values()), key=lambda x: x['kind'], reverse=True)

	@property
	@lazy
	def modaction_num(self):
		if self.admin_level < 2: return 0
		return g.db.query(ModAction.id).filter_by(user_id=self.id).count()

	@property
	@lazy
	def notifications_count(self):
		notifs = g.db.query(Notification.user_id).join(Comment).filter(Notification.user_id == self.id, Notification.read == False, Comment.is_banned == False, Comment.deleted_utc == 0)
		
		if not self.shadowbanned and self.admin_level < 3:
			notifs = notifs.join(User, User.id == Comment.author_id).filter(User.shadowbanned == None)
		
		return notifs.count()

	@property
	@lazy
	def post_notifications_count(self):
		return g.db.query(Notification.user_id).join(Comment).filter(Notification.user_id == self.id, Notification.read == False, Comment.author_id == AUTOJANNY_ID).count()

	@property
	@lazy
	def reddit_notifications_count(self):
		return g.db.query(Notification.user_id).join(Comment).filter(Notification.user_id == self.id, Notification.read == False, Comment.is_banned == False, Comment.deleted_utc == 0, Comment.body_html.like('%<p>New site mention: <a href="https://old.reddit.com/r/%'), Comment.parent_submission == None, Comment.author_id == NOTIFICATIONS_ID).count()

	@property
	@lazy
	def normal_count(self):
		return self.notifications_count - self.post_notifications_count - self.reddit_notifications_count

	@property
	@lazy
	def do_posts(self):
		return self.post_notifications_count and self.notifications_count-self.reddit_notifications_count == self.post_notifications_count

	@property
	@lazy
	def do_reddit(self):
		return self.notifications_count == self.reddit_notifications_count

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

	@property
	@lazy
	def moderated_subs(self):
		modded_subs = g.db.query(Mod.sub).filter_by(user_id=self.id).all()
		return modded_subs

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
				'post_count': 0 if self.shadowbanned and not (v and (v.shadowbanned or v.admin_level > 1)) else self.post_count,
				'comment_count': 0 if self.shadowbanned and not (v and (v.shadowbanned or v.admin_level > 1)) else self.comment_count,
				'badges': [x.path for x in self.badges],
				}

		return data

	@lazy
	def json_notes(self, v):
		data = {'username': self.username,
				'url': self.url,
				'id': self.id,
				'notes': [x.json() for x in self.notes]
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
		data = self.json_core

		data["badges"] = [x.json for x in self.badges]
		data['coins'] = self.coins
		data['post_count'] = self.post_count
		data['comment_count'] = self.comment_count

		return data


	def ban(self, admin=None, reason=None, days=0):
		if days:
			self.unban_utc = int(time.time()) + (days * 86400)
			g.db.add(self)

		self.is_banned = admin.id if admin else AUTOJANNY_ID
		if reason: self.ban_reason = reason

	@property
	def is_suspended(self):
		return (self.is_banned and (self.unban_utc == 0 or self.unban_utc > time.time()))

	@property
	def is_suspended_permanently(self):
		return (self.is_banned and self.unban_utc == 0)

	@property
	@lazy
	def applications(self):
		return g.db.query(OauthApp).filter_by(author_id=self.id).order_by(OauthApp.id)

	@property
	@lazy
	def created_datetime(self):
		return time.strftime("%d/%B/%Y %H:%M:%S UTC", time.gmtime(self.created_utc))

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
	def saved_idlist(self, page=1):
		saved = [x[0] for x in g.db.query(SaveRelationship.submission_id).filter_by(user_id=self.id).all()]
		posts = g.db.query(Submission.id).filter(Submission.id.in_(saved), Submission.is_banned == False, Submission.deleted_utc == 0)

		if self.admin_level < 2:
			posts = posts.filter(Submission.author_id.notin_(self.userblocks))

		return [x[0] for x in posts.order_by(Submission.created_utc.desc()).offset(25 * (page - 1)).all()]

	@lazy
	def saved_comment_idlist(self, page=1):
		saved = [x[0] for x in g.db.query(CommentSaveRelationship.comment_id).filter_by(user_id=self.id).all()]
		comments = g.db.query(Comment.id).filter(Comment.id.in_(saved), Comment.is_banned == False, Comment.deleted_utc == 0)

		if self.admin_level < 2:
			comments = comments.filter(Comment.author_id.notin_(self.userblocks))

		return [x[0] for x in comments.order_by(Comment.created_utc.desc()).offset(25 * (page - 1)).all()]

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
			if self.author_id == target.author_id: return True
			return self.admin_level >= PERMS['POST_EDITING']
		if isinstance(target, ScheduledSubmissionTask):
			return self.admin_level >= PERMS['SCHEDULER_POSTS']

	@property
	def can_see_shadowbanned(self):
		return self.admin_level >= PERMS['USER_SHADOWBAN'] or self.shadowbanned
