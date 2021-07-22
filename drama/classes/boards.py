from sqlalchemy.orm import lazyload
from .userblock import *
from .submission import *
from .board_relationships import *
from .comment import Comment
from .mix_ins import *
from drama.__main__ import Base, cache


class Board(Base, Stndrd, Age_times):

	__tablename__ = "boards"

	id = Column(Integer, primary_key=True)
	name = Column(String)
	created_utc = Column(Integer)
	description = Column(String)

	description_html=Column(String)
	over_18=Column(Boolean, default=False)
	is_nsfl=Column(Boolean, default=False)
	is_banned=Column(Boolean, default=False)
	disablesignups=Column(Boolean, default=False)
	has_banner=Column(Boolean, default=False)
	has_profile=Column(Boolean, default=False)
	creator_id=Column(Integer, ForeignKey("users.id"))
	ban_reason=Column(String(256), default=None)
	color=Column(String(8), default="FF66AC")
	restricted_posting=Column(Boolean, default=False)
	hide_banner_data=Column(Boolean, default=False)
	profile_nonce=Column(Integer, default=0)
	banner_nonce=Column(Integer, default=0)
	is_private=Column(Boolean, default=False)
	color_nonce=Column(Integer, default=0)
	rank_trending=Column(Float, default=0)
	stored_subscriber_count=Column(Integer, default=1)
	all_opt_out=Column(Boolean, default=False)
	is_siegable=Column(Boolean, default=True)
	secondary_color=Column(String(6), default="cfcfcf")
	motd = Column(String(1000), default='')

	moderators=relationship("ModRelationship")
	submissions=relationship("Submission", primaryjoin="Board.id==Submission.board_id")
	contributors=relationship("ContributorRelationship", lazy="dynamic")
	bans=relationship("BanRelationship", lazy="dynamic")
	postrels=relationship("PostRelationship", lazy="dynamic")
	trending_rank=deferred(Column(Float, server_default=FetchedValue()))

	# db side functions
	subscriber_count = deferred(Column(Integer, server_default=FetchedValue()))

	def __init__(self, **kwargs):

		kwargs["created_utc"] = int(time.time())

		super().__init__(**kwargs)

	def __repr__(self):
		return f"<Board(name={self.name})>"

	@property
	def fullname(self):
		return f"t4_{self.base36id}"

	@property
	def mods_list(self):

		z = [x for x in self.moderators if x.accepted and not (
			x.user.is_deleted or (x.user.is_banned and not x.user.unban_utc))]

		z = sorted(z, key=lambda x: x.created_utc)
		return z

	@property
	def mods(self):

		z = [x for x in self.moderators if x.accepted]

		z = sorted(z, key=lambda x: x.created_utc)

		z = [x.user for x in z]

		return z

	@property
	def invited_mods(self):

		z = [x.user for x in self.moderators if x.accepted ==
			 False and x.invite_rescinded == False]
		z = sorted(z, key=lambda x: x.created_utc)
		return z

	@property
	def mod_invites(self):
		z = [x for x in self.moderators if x.accepted ==
			 False and x.invite_rescinded == False]
		z = sorted(z, key=lambda x: x.created_utc)
		return z

	@property
	def mods_count(self):

		return len(self.mods_list)

	@property
	def permalink(self):

		return f"/+{self.name}"

	def can_take(self, post):
		if self.is_banned:
			return False
		return not self.postrels.filter_by(post_id=post.id).first()

	def has_mod(self, user, perm=None):

		if user is None:
			return None

		if self.is_banned:
			return False

		m=self.__dict__.get("_mod")
		if not m:
			for x in user.moderates:
				if x.board_id == self.id and x.accepted and not x.invite_rescinded:
					self.__dict__["mod"]=x
					m=x
		
		if not m:
			return False
					
		if perm:

			return m if (m.perm_full or m.__dict__[f"perm_{perm}"]) else False

		else:
			return m


		return False

	def has_mod_record(self, user, perm=None):

		if user is None:
			return None

		if self.is_banned:
			return False

		for x in user.moderates:
			if x.board_id == self.id and not x.invite_rescinded:
				
				if perm:
					return x if x.__dict__[f"perm_{perm}"] else False
				else:
					return x


		return False
	def can_invite_mod(self, user):

		return user.id not in [
			x.user_id for x in self.moderators if not x.invite_rescinded]

	def has_rescinded_invite(self, user):

		return user.id in [
			x.user_id for x in self.moderators if x.invite_rescinded == True]

	def has_invite(self, user):

		if user is None:
			return None

		for x in [
				i for i in self.moderators if not i.invite_rescinded and not i.accepted]:

			if x.user_id == user.id:
				return x

		return None

	def has_ban(self, user):

		if user is None:
			return None
		
		if user.admin_level >=2:
			return None

		return g.db.query(BanRelationship).filter_by(
			board_id=self.id, user_id=user.id, is_active=True).first()

	def has_contributor(self, user):

		if user is None:
			return False

		return g.db.query(ContributorRelationship).filter_by(
			user_id=user.id, board_id=self.id, is_active=True).first()

	def can_submit(self, user):

		if user is None:
			return False

		if user.admin_level >= 4:
			return True

		if self.has_ban(user):
			return False

		if self.has_contributor(user) or self.has_mod(user):
			return True

		if self.is_private or self.restricted_posting:
			return False

		return True

	def can_comment(self, user):

		if user is None:
			return False

		if user.admin_level >= 4:
			return True

		if self.has_ban(user):
			return False

		if self.has_contributor(user) or self.has_mod(user):
			return True

		if self.is_private:
			return False

		return True

	def can_view(self, user):

		if user is None:
			return False

		if user.admin_level >= 4:
			return True

		if self.has_contributor(user) or self.has_mod(
				user) or self.has_invite(user):
			return True

		if self.is_private:
			return False

	@property
	def banner_url(self):
		return "/assets/images/preview.png"

	@property
	def profile_url(self):
			return "/assets/images/favicon.png"

	@property
	def css_url(self):
		return f"/assets/{self.fullname}/main/{self.color_nonce}.css"

	@property
	def css_dark_url(self):
		return f"/assets/{self.fullname}/dark/{self.color_nonce}.css"

	def has_participant(self, user):
		return (g.db.query(Submission).filter_by(original_board_id=self.id, author_id=user.id).first() or
				g.db.query(Comment).filter_by(
			author_id=user.id, original_board_id=self.id).first()
		)

	@property
	@lazy
	def n_pins(self):
		return g.db.query(Submission).filter_by(
			board_id=self.id, is_pinned=True).count()

	@property
	def can_pin_another(self):

		return self.n_pins < 4

	@property
	def json_core(self):

		if self.is_banned:
			return {'name': self.name,
					'permalink': self.permalink,
					'is_banned': True,
					'ban_reason': self.ban_reason,
					'id': self.base36id
					}
		return {'name': self.name,
				'profile_url': self.profile_url,
				'banner_url': self.banner_url,
				'created_utc': self.created_utc,
				'permalink': self.permalink,
				'description': self.description,
				'description_html': self.description_html,
				'over_18': self.over_18,
				'is_banned': False,
				'is_private': self.is_private,
				'is_restricted': self.restricted_posting,
				'id': self.base36id,
				'fullname': self.fullname,
				'banner_url': self.banner_url,
				'profile_url': self.profile_url,
				'color': "#" + self.color,
				'is_siege_protected': not self.is_siegable
				}

	@property
	def json(self):
		data=self.json_core

		if self.is_banned:
			return data


		data['guildmasters']=[x.json_core for x in self.mods]
		data['subscriber_count']= self.subscriber_count

		return data
	

	@property
	def show_settings_icons(self):
		return self.is_private or self.restricted_posting or self.over_18 or self.all_opt_out

	@cache.memoize(600)
	def comment_idlist(self, page=1, v=None, nsfw=False, **kwargs):

		posts = g.db.query(Submission).options(
			lazyload('*')).filter_by(board_id=self.id)

		if not nsfw:
			posts = posts.filter_by(over_18=False)

		if v and not v.show_nsfl:
			posts = posts.filter_by(is_nsfl=False)

		if self.is_private:
			if v and (self.can_view(v) or v.admin_level >= 4):
				pass
			elif v:
				posts = posts.filter(or_(Submission.post_public == True,
										 Submission.author_id == v.id
										 )
									 )
			else:
				posts = posts.filter_by(post_public=True)

		posts = posts.subquery()

		comments = g.db.query(Comment).options(lazyload('*'))

		if v and v.hide_offensive:
			comments = comments.filter_by(is_offensive=False)
			
		if v and v.hide_bot:
			comments = comments.filter_by(is_bot=False)

		if v and not self.has_mod(v) and v.admin_level <= 3:
			# blocks
			blocking = g.db.query(
				UserBlock.target_id).filter_by(
				user_id=v.id).subquery()
			blocked = g.db.query(
				UserBlock.user_id).filter_by(
				target_id=v.id).subquery()

			comments = comments.filter(
				Comment.author_id.notin_(blocking),
				Comment.author_id.notin_(blocked)
			)

		if not v or not v.admin_level >= 3:
			comments = comments.filter_by(is_banned=False).filter(Comment.deleted_utc == 0)

		comments = comments.join(
			posts, Comment.parent_submission == posts.c.id)

		comments = comments.order_by(Comment.created_utc.desc()).offset(
			25 * (page - 1)).limit(26).all()

		return [x.id for x in comments]


	def user_guild_rep(self, user):

		return user.guild_rep(self)

	def is_guildmaster(self, perm=None):
		mod=self.__dict__.get('_is_guildmaster', False)
		if not mod:
			return False
		if not perm:
			return True

		return mod.__dict__[f"perm_{perm}"]


	@property
	def siege_rep_requirement(self):

		now=int(time.time())

		return self.stored_subscriber_count//10 + min(180, (now-self.created_utc)//(60*60*24))