from sqlalchemy.orm import deferred, contains_eager, aliased
from secrets import token_hex
import pyotp

from ruqqus.helpers.discord import delete_role
from ruqqus.helpers.aws import *
from .alts import Alt
from .titles import Title
from .submission import SaveRelationship
from .comment import Notification
from .boards import Board
from .board_relationships import *
from .subscriptions import *
from .userblock import *
from .badges import *
from .clients import *
from .paypal import PayPalTxn
from ruqqus.__main__ import Base, cache
from ruqqus.helpers.security import *

class User(Base, Stndrd, Age_times):
	__tablename__ = "users"
	id = Column(Integer, primary_key=True)
	username = Column(String, default=None)
	namecolor = Column(String, default='ff66ac')
	customtitle = Column(String, default=None)
	customtitleplain = Column(String, default=None)
	titlecolor = Column(String, default='ff66ac')
	theme = Column(String, default='dark')
	themecolor = Column(String, default='ff66ac')
	song = Column(String, default=None)
	profileurl = Column(String, default=None)
	bannerurl = Column(String, default=None)
	email = Column(String, default=None)
	css = deferred(Column(String, default=None))
	profilecss = deferred(Column(String, default=None))
	passhash = deferred(Column(String, default=None))
	created_utc = Column(Integer, default=0)
	admin_level = Column(Integer, default=0)
	agendaposter = Column(Boolean, default=False)
	agendaposter_expires_utc = Column(Integer, default=0)
	changelogsub = Column(Boolean, default=False)
	is_activated = Column(Boolean, default=False)
	shadowbanned = Column(Boolean, default=False)
	over_18 = Column(Boolean, default=False)
	hidevotedon = Column(Boolean, default=False)
	slurreplacer = Column(Boolean, default=True)
	flairchanged = Column(Boolean, default=False)
	newtab = Column(Boolean, default=False)
	newtabexternal = Column(Boolean, default=True)
	oldreddit = Column(Boolean, default=False)
	creation_ip = Column(String, default=None)
	submissions = relationship(
		"Submission",
		lazy="dynamic",
		primaryjoin="Submission.author_id==User.id",
		backref="author_rel")
	comments = relationship(
		"Comment",
		lazy="dynamic",
		primaryjoin="Comment.author_id==User.id")
	votes = relationship("Vote", lazy="dynamic", backref="users")
	commentvotes = relationship("CommentVote", lazy="dynamic", backref="users")
	bio = Column(String, default="")
	bio_html = Column(String, default="")
	badges = relationship("Badge", lazy="dynamic", backref="user")
	real_id = Column(String, default=None)
	notifications = relationship(
		"Notification",
		lazy="dynamic")

	# unread_notifications_relationship=relationship(
	#	"Notification",
	#	primaryjoin="and_(Notification.user_id==User.id, Notification.read==False)")

	referred_by = Column(Integer, default=None)
	is_banned = Column(Integer, default=0)
	unban_utc = Column(Integer, default=0)
	ban_reason = Column(String, default="")
	feed_nonce = Column(Integer, default=0)
	login_nonce = Column(Integer, default=0)
	title_id = Column(Integer, ForeignKey("titles.id"), default=None)
	title = relationship("Title", lazy="joined")
	has_profile = Column(Boolean, default=False)
	has_banner = Column(Boolean, default=False)
	reserved = Column(String(256), default=None)
	is_nsfw = Column(Boolean, default=False)
	tos_agreed_utc = Column(Integer, default=0)
	profile_nonce = Column(Integer, default=0)
	banner_nonce = Column(Integer, default=0)
	last_siege_utc = Column(Integer, default=0)
	mfa_secret = deferred(Column(String(16), default=None))
	hide_offensive = Column(Boolean, default=False)
	hide_bot = Column(Boolean, default=False)
	show_nsfl = Column(Boolean, default=False)
	is_private = Column(Boolean, default=False)
	read_announcement_utc = Column(Integer, default=0)
	unban_utc = Column(Integer, default=0)

	is_deleted = Column(Boolean, default=False)
	delete_reason = Column(String(500), default='')
	filter_nsfw = Column(Boolean, default=False)
	stored_subscriber_count = Column(Integer, default=0)
	defaultsortingcomments = Column(String, default="top")
	defaultsorting = Column(String, default="hot")
	defaulttime = Column(String, default="all")
	coin_balance = Column(Integer, default=0)
	premium_expires_utc = Column(Integer, default=0)
	negative_balance_cents = Column(Integer, default=0)

	is_nofollow = Column(Boolean, default=False)
	custom_filter_list = Column(String(1000), default="")
	discord_id = Column(String(64), default=None)
	creation_region = Column(String(2), default=None)
	ban_evade = Column(Integer, default=0)

	profile_upload_ip = deferred(Column(String(255), default=None))
	banner_upload_ip = deferred(Column(String(255), default=None))
	profile_upload_region = deferred(Column(String(2)))
	banner_upload_region = deferred(Column(String(2)))

	# stuff to support name changes
	profile_set_utc = deferred(Column(Integer, default=0))
	banner_set_utc = deferred(Column(Integer, default=0))
	original_username = deferred(Column(String(255)))
	name_changed_utc = deferred(Column(Integer, default=0))

	moderates = relationship("ModRelationship")
	banned_from = relationship("BanRelationship", primaryjoin="BanRelationship.user_id==User.id")
	subscriptions = relationship("Subscription")
	boards_created = relationship("Board", lazy="dynamic")
	contributes = relationship(
		"ContributorRelationship",
		lazy="dynamic",
		primaryjoin="ContributorRelationship.user_id==User.id")
	board_blocks = relationship("BoardBlock", lazy="dynamic")

	following = relationship("Follow", primaryjoin="Follow.user_id==User.id")
	followers = relationship("Follow", primaryjoin="Follow.target_id==User.id")

	blocking = relationship("UserBlock", lazy="dynamic", primaryjoin="User.id==UserBlock.user_id")
	blocked = relationship("UserBlock", lazy="dynamic", primaryjoin="User.id==UserBlock.target_id")

	_applications = relationship("OauthApp", lazy="dynamic")
	authorizations = relationship("ClientAuth", lazy="dynamic")

	saved_posts = relationship(
		"SaveRelationship",
		lazy="dynamic",
		primaryjoin="User.id==SaveRelationship.user_id")

	_transactions = relationship(
		"PayPalTxn",
		lazy="dynamic",
		primaryjoin="PayPalTxn.user_id==User.id")

	# properties defined as SQL server-side functions
	referral_count = deferred(Column(Integer, server_default=FetchedValue()))
	follower_count = deferred(Column(Integer, server_default=FetchedValue()))

	def __init__(self, **kwargs):

		if "password" in kwargs:
			kwargs["passhash"] = self.hash_password(kwargs["password"])
			kwargs.pop("password")

		kwargs["created_utc"] = int(time.time())

		super().__init__(**kwargs)

	@property
	@lazy
	def dramacoins(self):
		posts = sum([x[0] - 1 for x in
					 g.db.query(Submission.score).options(lazyload('*')).filter_by(author_id=self.id, is_banned=False,
																				   deleted_utc=0).all()])
		comments = sum([x[0] - 1 for x in
						g.db.query(Comment.score).options(lazyload('*')).filter_by(author_id=self.id, is_banned=False,
																				   deleted_utc=0).all()])
		return int(posts + comments)

	def has_block(self, target):

		return g.db.query(UserBlock).filter_by(
			user_id=self.id, target_id=target.id).first()

	def is_blocked_by(self, user):

		return g.db.query(UserBlock).filter_by(
			user_id=user.id, target_id=self.id).first()

	def any_block_exists(self, other):

		return g.db.query(UserBlock).filter(
			or_(and_(UserBlock.user_id == self.id, UserBlock.target_id == other.id), and_(
				UserBlock.user_id == other.id, UserBlock.target_id == self.id))).first()

	def has_blocked_guild(self, board):

		return g.db.query(BoardBlock).filter_by(
			user_id=self.id, board_id=board.id).first()

	def validate_2fa(self, token):

		x = pyotp.TOTP(self.mfa_secret)
		return x.verify(token, valid_window=1)

	@property
	def age(self):
		return int(time.time()) - self.created_utc

	@property
	def strid(self):
		return str(self.id)

	@cache.memoize(300)
	def userpagelisting(self, v=None, page=1, sort="new", t="all"):

		submissions = g.db.query(Submission).options(lazyload('*')).filter_by(author_id=self.id, is_pinned=False)

		if not (v and (v.admin_level >= 3 or v.id == self.id)):
			submissions = submissions.filter_by(deleted_utc=0)
			submissions = submissions.filter_by(is_banned=False)

		now = int(time.time())
		if t == 'hour':
			cutoff = now - 3600
		elif t == 'day':
			cutoff = now - 86400
		elif t == 'week':
			cutoff = now - 604800
		elif t == 'month':
			cutoff = now - 2592000
		elif t == 'year':
			cutoff = now - 31536000
		else:
			cutoff = 0
		submissions = submissions.filter(Submission.created_utc >= cutoff)

		if sort == "new":
			submissions = submissions.order_by(Submission.created_utc.desc()).all()
		elif sort == "old":
			submissions = submissions.order_by(Submission.created_utc.asc()).all()
		elif sort == "controversial":
			submissions = sorted(submissions.all(), key=lambda x: x.score_disputed, reverse=True)
		elif sort == "top":
			submissions = submissions.order_by(Submission.score.desc()).all()
		elif sort == "bottom":
			submissions = submissions.order_by(Submission.score.asc()).all()
		elif sort == "comments":
			submissions = submissions.order_by(Submission.comment_count.desc()).all()

		firstrange = 25 * (page - 1)
		secondrange = firstrange + 26
		listing = [x.id for x in submissions[firstrange:secondrange]]
		return listing

	@cache.memoize(300)
	def commentlisting(self, v=None, page=1, sort="new", t="all"):
		comments = self.comments.options(lazyload('*')).filter(Comment.parent_submission is not None).join(Comment.post)

		if (not v) or (v.id != self.id and v.admin_level == 0):
			comments = comments.filter(Comment.deleted_utc == 0)
			comments = comments.filter(Comment.is_banned == False)

		if v and v.admin_level >= 4:
			pass
		elif v:
			m = g.db.query(ModRelationship).filter_by(user_id=v.id, invite_rescinded=False).subquery()
			c = v.contributes.subquery()

			comments = comments.join(m,
									 m.c.board_id == Submission.board_id,
									 isouter=True
									 ).join(c,
											c.c.board_id == Submission.board_id,
											isouter=True
											).join(Board, Board.id == Submission.board_id)
			comments = comments.filter(or_(Comment.author_id == v.id,
										   Submission.post_public == True,
										   Board.is_private == False,
										   m.c.board_id != None,
										   c.c.board_id != None))
		else:
			comments = comments.join(Board, Board.id == Submission.board_id).filter(
				or_(Submission.post_public == True, Board.is_private == False))

		comments = comments.options(contains_eager(Comment.post))

		now = int(time.time())
		if t == 'hour':
			cutoff = now - 3600
		elif t == 'day':
			cutoff = now - 86400
		elif t == 'week':
			cutoff = now - 604800
		elif t == 'month':
			cutoff = now - 2592000
		elif t == 'year':
			cutoff = now - 31536000
		else:
			cutoff = 0
		comments = comments.filter(Comment.created_utc >= cutoff)

		if sort == "new":
			comments = comments.order_by(Comment.created_utc.desc()).all()
		elif sort == "old":
			comments = comments.order_by(Comment.created_utc.asc()).all()
		elif sort == "controversial":
			comments = sorted(comments.all(), key=lambda x: x.score_disputed, reverse=True)
		elif sort == "top":
			comments = comments.order_by(Comment.score.desc()).all()
		elif sort == "bottom":
			comments = comments.order_by(Comment.score.asc()).all()

		firstrange = 25 * (page - 1)
		secondrange = firstrange + 26
		return [x.id for x in comments[firstrange:secondrange]]

	@property
	@lazy
	def mods_anything(self):

		return bool([i for i in self.moderates if i.accepted])

	@property
	def boards_modded(self):

		z = [x.board for x in self.moderates if x and x.board and x.accepted and not x.board.is_banned]
		z = sorted(z, key=lambda x: x.name)

		return z

	@property
	def base36id(self):
		return base36encode(self.id)

	@property
	def fullname(self):
		return f"t1_{self.base36id}"

	@property
	@cache.memoize(timeout=60)
	def has_report_queue(self):
		board_ids = [
			x.board_id for x in self.moderates.filter_by(
				accepted=True).all()]
		return bool(g.db.query(Submission).filter(Submission.board_id.in_(
			board_ids), Submission.mod_approved == 0, Submission.is_banned == False).join(Submission.reports).first())

	@property
	def banned_by(self):

		if not self.is_banned:
			return None

		return g.db.query(User).filter_by(id=self.is_banned).first()

	def has_badge(self, badgedef_id):
		return self.badges.filter_by(badge_id=badgedef_id).first()
	
	@property
	@lazy
	def patron(self):
		if self.has_badge(21) or self.has_badge(22) or self.has_badge(23) or self.has_badge(24): return True
		else: return False

	def vote_status_on_post(self, post):

		return post.voted

	def vote_status_on_comment(self, comment):

		return comment.voted

	def hash_password(self, password):
		return generate_password_hash(
			password, method='pbkdf2:sha512', salt_length=8)

	def verifyPass(self, password):
		return check_password_hash(self.passhash, password)

	@property
	def feedkey(self):

		return generate_hash(f"{self.username}{self.id}{self.feed_nonce}{self.created_utc}")

	@property
	def formkey(self):

		if "session_id" not in session:
			session["session_id"] = token_hex(16)

		msg = f"{session['session_id']}+{self.id}+{self.login_nonce}"

		return generate_hash(msg)

	def validate_formkey(self, formkey):

		return validate_hash(f"{session['session_id']}+{self.id}+{self.login_nonce}", formkey)

	@property
	def url(self):
		return f"/@{self.username}"

	@property
	def permalink(self):
		return self.url

	@property
	def uid_permalink(self):
		return f"/uid/{self.base36id}"

	@property
	def original_link(self):
		return f"/@{self.original_username}"

	def __repr__(self):
		return f"<User(username={self.username})>"

	@property
	@lazy
	def post_notifications_count(self):
		return self.notifications.filter(Notification.read == False).join(Notification.comment).filter(
			Comment.author_id == 2360).count()

	def notification_subscriptions(self, page=1, all_=False):

		notifications = self.notifications.join(Notification.comment).filter(Comment.author_id == 2360)

		notifications = notifications.options(
			contains_eager(Notification.comment)
		)

		notifications = notifications.order_by(Notification.id.desc()).offset(25 * (page - 1)).limit(26)

		output = []
		for x in notifications:
			x.read = True
			g.db.add(x)
			output.append(x.comment_id)

		g.db.commit()
		return output

	def notification_commentlisting(self, page=1, all_=False):

		notifications = self.notifications.join(Notification.comment).filter(
			Comment.is_banned == False,
			Comment.deleted_utc == 0,
			Comment.author_id != 2360,
		)

		if not all_:
			notifications = notifications.filter(Notification.read == False)

		notifications = notifications.options(
			contains_eager(Notification.comment)
		)

		notifications = notifications.order_by(
			Notification.id.desc()).offset(25 * (page - 1)).limit(26)

		output = []
		for x in notifications:
			x.read = True
			g.db.add(x)
			output.append(x.comment_id)
		return output

	@property
	@lazy
	def notifications_count(self):

		return self.notifications.join(Notification.comment).filter(Notification.read == False,
																	Comment.is_banned == False,
																	Comment.deleted_utc == 0).count()

	@property
	def post_count(self):

		return self.submissions.filter_by(is_banned=False, deleted_utc=0).count()

	@property
	def comment_count(self):

		return self.comments.filter(Comment.parent_submission != None).filter_by(is_banned=False, deleted_utc=0).count()

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
		).order_by(User.username.asc()).all()

		data = [x for x in data]
		output = []
		for x in data:
			user = x[0]
			user._is_manual = x[1].is_manual
			output.append(user)

		return output

	def alts_subquery(self):
		return g.db.query(User.id).filter(
			or_(
				User.id.in_(
					g.db.query(Alt.user1).filter(
						Alt.user2 == self.id
					).subquery()
				),
				User.id.in_(
					g.db.query(Alt.user2).filter(
						Alt.user1 == self.id
					).subquery()
				).subquery()
			)
		).subquery()

	def alts_threaded(self, db):

		subq = db.query(Alt).filter(
			or_(
				Alt.user1 == self.id,
				Alt.user2 == self.id
			)
		).subquery()

		data = db.query(
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
		).order_by(User.username.asc()).all()

		data = [x for x in data]
		output = []
		for x in data:
			user = x[0]
			user._is_manual = x[1].is_manual
			output.append(user)

		return output

	def has_follower(self, user):

		return g.db.query(Follow).filter_by(
			target_id=self.id, user_id=user.id).first()

	def set_profile(self, file):

		self.del_profile()
		self.profile_nonce += 1

		imageurl = upload_file(name=f"profile.gif", file=file, resize=(100, 100))
		if imageurl:
			self.profileurl = imageurl
			self.has_profile = True
			self.profile_upload_ip = request.remote_addr
			self.profile_set_utc = int(time.time())
			self.profile_upload_region = request.headers.get("cf-ipcountry")
			g.db.add(self)

	def set_banner(self, file):

		self.del_banner()
		self.banner_nonce += 1

		imageurl = upload_file(name=f"banner.gif", file=file)
		if imageurl:
			self.bannerurl = imageurl
			self.has_banner = True
			self.banner_upload_ip = request.remote_addr
			self.banner_set_utc = int(time.time())
			self.banner_upload_region = request.headers.get("cf-ipcountry")
			g.db.add(self)

	def del_profile(self):

		self.has_profile = False
		g.db.add(self)

	def del_banner(self):

		self.has_banner = False
		g.db.add(self)

	@property
	def banner_url(self):
		if self.has_banner:
			if self.bannerurl:
				return self.bannerurl
			else:
				return f"https://s3.eu-central-1.amazonaws.com/i.ruqqus.ga/uid/{self.base36id}/banner-{self.banner_nonce}.png"
		else:
			return "/assets/images/default_bg.png"

	@cache.memoize(0)
	def defaultpicture(self):
		pic = random.randint(1, 50)
		return f"/assets/images/defaultpictures/{pic}.png"

	@property
	def profile_url(self):
		if self.has_profile and not self.is_deleted:
			if self.profileurl:
				return self.profileurl
			else:
				return f"https://s3.eu-central-1.amazonaws.com/i.ruqqus.ga/uid/{self.base36id}/profile-{self.profile_nonce}.png"
		else:
			return self.defaultpicture()

	@property
	def available_titles(self):

		locs = {"v": self,
				"Board": Board,
				"Submission": Submission
				}

		titles = [
			i for i in g.db.query(Title).order_by(
				text("id asc")).all() if eval(
				i.qualification_expr, {}, locs)]
		return titles

	@property
	def can_make_guild(self):
		return False

	# return (self.has_premium or self.dramacoins >= 250 or (self.created_utc <= 1592974538 and self.dramacoins >= 50)) and len([x for x in self.boards_modded if x.is_siegable]) < 10

	@property
	def can_join_gms(self):
		return len([x for x in self.boards_modded if x.is_siegable]) < 10

	@property
	def can_siege(self):

		if self.is_suspended:
			return False

		now = int(time.time())

		return now - max(self.last_siege_utc,
						 self.created_utc) > 60 * 60 * 24 * 7

	@property
	def can_submit_image(self):
		# Has premium
		# Has 1000 Rep, or 500 for older accounts
		# if connecting through Tor, must have verified email
		return (self.has_premium or self.dramacoins >= 0 or (
				self.created_utc <= 1592974538 and self.dramacoins >= 500)) and (
						   self.is_activated or request.headers.get("cf-ipcountry") != "T1")

	@property
	def can_upload_avatar(self):
		return (self.has_premium or self.dramacoins >= 0 or self.created_utc <= 1592974538) and (
					self.is_activated or request.headers.get("cf-ipcountry") != "T1")

	@property
	def can_upload_banner(self):
		return (self.has_premium or self.dramacoins >= 0 or self.created_utc <= 1592974538) and (
					self.is_activated or request.headers.get("cf-ipcountry") != "T1")

	@property
	def json_raw(self):
		data = {'username': self.username,
				'permalink': self.permalink,
				'is_banned': bool(self.is_banned),
				'is_premium': self.has_premium_no_renew,
				'created_utc': self.created_utc,
				'id': self.base36id,
				'is_private': self.is_private,
				'profile_url': self.profile_url,
				'banner_url': self.banner_url,
				'title': self.title.json if self.title else None,
				'bio': self.bio,
				'bio_html': self.bio_html,
				'flair': self.customtitle
				}

		if self.real_id:
			data['real_id'] = self.real_id

		return data

	@property
	def json_core(self):

		now = int(time.time())
		if self.is_banned and (self.unban_utc == 0 or now < self.unban_utc):
			return {'username': self.username,
					'permalink': self.permalink,
					'is_banned': True,
					'is_permanent_ban': not bool(self.unban_utc),
					'ban_reason': self.ban_reason,
					'id': self.base36id
					}

		elif self.is_deleted:
			return {'username': self.username,
					'permalink': self.permalink,
					'is_deleted': True,
					'id': self.base36id
					}
		return self.json_raw

	@property
	def json(self):
		data = self.json_core

		if self.is_deleted or self.is_banned:
			return data

		data["badges"] = [x.json_core for x in self.badges]
		data['dramacoins'] = int(self.dramacoins)
		data['post_count'] = self.post_count
		data['comment_count'] = self.comment_count

		return data

	@property
	def can_use_darkmode(self):
		return True

	# return self.referral_count or self.has_earned_darkmode or
	# self.has_badge(16) or self.has_badge(17)

	@property
	def is_valid(self):
		if self.is_banned and self.unban_utc == 0:
			return False

		elif self.is_deleted:
			return False

		else:
			return True

	def ban(self, admin=None, reason=None, days=0):

		if days > 0:
			ban_time = int(time.time()) + (days * 86400)
			self.unban_utc = ban_time

		else:
			self.unban_utc = 0
			if self.has_banner:
				self.del_banner()
			if self.has_profile:
				self.del_profile()

			delete_role(self, "linked")

		self.is_banned = admin.id if admin else 2317
		if reason:
			self.ban_reason = reason

		try:
			g.db.add(self)
		except:
			pass

	def unban(self):

		# Takes care of all functions needed for account reinstatement.

		self.is_banned = None
		self.unban_utc = None

		g.db.add(self)

	@property
	def is_suspended(self):
		return (self.is_banned and (self.unban_utc ==
									0 or self.unban_utc > time.time()))

	@property
	def is_blocking(self):
		return self.__dict__.get('_is_blocking', 0)

	@property
	def is_blocked(self):
		return self.__dict__.get('_is_blocked', 0)

	def refresh_selfset_badges(self):

		# check self-setting badges
		badge_types = g.db.query(BadgeDef).filter(
			BadgeDef.qualification_expr.isnot(None)).all()
		for badge in badge_types:
			if eval(badge.qualification_expr, {}, {'v': self}):
				if not self.has_badge(badge.id):
					new_badge = Badge(user_id=self.id,
									  badge_id=badge.id,
									  created_utc=int(time.time())
									  )
					g.db.add(new_badge)

			else:
				bad_badge = self.has_badge(badge.id)
				if bad_badge:
					g.db.delete(bad_badge)

		try:
			g.db.add(self)
		except:
			pass

	@property
	def applications(self):
		return [x for x in self._applications.order_by(
			OauthApp.id.asc()).all()]

	def subscribed_idlist(self, page=1):
		posts = g.db.query(Subscription.submission_id).filter_by(user_id=self.id).all()
		return [x[0] for x in posts]

	def saved_idlist(self, page=1):

		posts = g.db.query(Submission.id).options(lazyload('*')).filter_by(is_banned=False,
																		   deleted_utc=0
																		   )

		saved = g.db.query(SaveRelationship.submission_id).filter(SaveRelationship.user_id == self.id).subquery()
		posts = posts.filter(Submission.id.in_(saved))

		if self.admin_level == 0:
			blocking = g.db.query(
				UserBlock.target_id).filter_by(
				user_id=self.id).subquery()
			blocked = g.db.query(
				UserBlock.user_id).filter_by(
				target_id=self.id).subquery()

			posts = posts.filter(
				Submission.author_id.notin_(blocking),
				Submission.author_id.notin_(blocked)
			)

		posts = posts.order_by(Submission.created_utc.desc())

		return [x[0] for x in posts.offset(25 * (page - 1)).limit(26).all()]

	def saved_comment_idlist(self, page=1):

		comments = g.db.query(Comment.id).options(lazyload('*')).filter_by(is_banned=False, deleted_utc=0)

		saved = g.db.query(SaveRelationship.submission_id).filter(SaveRelationship.user_id == self.id).subquery()
		comments = comments.filter(Comment.id.in_(saved))

		if self.admin_level == 0:
			blocking = g.db.query(
				UserBlock.target_id).filter_by(
				user_id=self.id).subquery()
			blocked = g.db.query(
				UserBlock.user_id).filter_by(
				target_id=self.id).subquery()

			comments = comments.filter(
				Comment.author_id.notin_(blocking),
				Comment.author_id.notin_(blocked)
			)

		comments = comments.order_by(Comment.created_utc.desc())

		return [x[0] for x in comments.offset(25 * (page - 1)).limit(26).all()]

	def guild_rep(self, guild, recent=0):

		posts = g.db.query(Submission.score).filter_by(
			is_banned=False,
			original_board_id=guild.id)

		if recent:
			cutoff = int(time.time()) - 60 * 60 * 24 * recent
			posts = posts.filter(Submission.created_utc > cutoff)

		posts = posts.all()

		post_rep = sum([x[0] for x in posts]) - len(list(sum([x[0] for x in posts])))

		comments = g.db.query(Comment.score).filter_by(
			is_banned=False,
			original_board_id=guild.id)

		if recent:
			cutoff = int(time.time()) - 60 * 60 * 24 * recent
			comments = comments.filter(Comment.created_utc > cutoff)

		comments = comments.all()

		comment_rep = sum([x[0] for x in comments]) - len(list(sum([x[0] for x in comments])))

		return int(post_rep + comment_rep)

	@property
	def has_premium(self):

		now = int(time.time())

		if self.negative_balance_cents:
			return False

		elif self.premium_expires_utc > now:
			return True

		elif self.coin_balance >= 1:
			self.coin_balance -= 1
			self.premium_expires_utc = now + 60 * 60 * 24 * 7

			g.db.add(self)

			return True

		else:

			if self.premium_expires_utc:
				self.premium_expires_utc = 0
				g.db.add(self)

			return False

	@property
	def has_premium_no_renew(self):

		now = int(time.time())

		if self.negative_balance_cents:
			return False
		elif self.premium_expires_utc > now:
			return True
		elif self.coin_balance >= 1:
			return True
		else:
			return False

	@property
	def renew_premium_time(self):
		return time.strftime("%d %b %Y at %H:%M:%S",
							 time.gmtime(self.premium_expires_utc))

	@property
	def filter_words(self):
		l = [i.strip() for i in self.custom_filter_list.split('\n')] if self.custom_filter_list else []
		l = [i for i in l if i]
		return l

	@property
	def boards_modded_ids(self):
		return [x.id for x in self.boards_modded]

	@property
	def txn_history(self):

		return self._transactions.filter(PayPalTxn.status != 1).order_by(PayPalTxn.created_utc.desc()).all()

	@property
	def json_admin(self):
		data = self.json_raw

		data['creation_ip'] = self.creation_ip
		data['creation_region'] = self.creation_region
		data['email'] = self.email
		data['email_verified'] = self.is_activated

		return data

	@property
	def can_upload_comment_image(self):
		return self.dramacoins >= 0 and (request.headers.get("cf-ipcountry") != "T1" or self.is_activated)

	@property
	def can_change_name(self):
		return True
# return self.name_changed_utc < int(time.time())-60*60*24*90
