import time
from urllib.parse import urlparse

from flask import g
from sqlalchemy import *
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Session, declared_attr, object_session, relationship

from files.classes.base import CreatedBase
from files.classes.flags import Flag
from files.classes.visstate import StateMod, StateReport, VisibilityState
from files.classes.votes import Vote, votes_shown_to
from files.helpers.assetcache import assetcache_path
from files.helpers.config.const import *
from files.helpers.config.environment import (SCORE_HIDING_TIME_HOURS, SITE,
                                              SITE_FULL, SITE_ID)
from files.helpers.content import body_displayed, is_web_url
from files.helpers.lazy import lazy
from files.helpers.locks import user_shadowbanned_locked
from files.helpers.time import format_age, format_datetime


# A post links an image when its URL ends (case-insensitively) in one of these, and points at the site or an embedding host (see is_image).
IMAGE_URL_SUFFIXES = ('.webp', '.jpg', '.png', '.gif', '.jpeg', '?maxwidth=9999', '&fidelity=high')


class Submission(CreatedBase):
	__tablename__ = "submissions"

	id = Column(Integer, primary_key=True)
	author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
	edited_utc = Column(Integer, default=0, nullable=False)
	thumburl = Column(String)
	bannedfor = Column(Boolean)
	ghost = Column(Boolean, default=False, nullable=False)
	views = Column(Integer, default=0, nullable=False)
	distinguish_level = Column(Integer, default=0, nullable=False)
	stickied = Column(String)
	stickied_utc = Column(Integer)
	is_pinned = Column(Boolean, default=False, nullable=False)
	private = Column(Boolean, default=False, nullable=False)
	comment_count = Column(Integer, default=0, nullable=False)
	over_18 = Column(Boolean, default=False, nullable=False)
	is_bot = Column(Boolean, default=False, nullable=False)
	upvotes = Column(Integer, default=1, nullable=False)
	downvotes = Column(Integer, default=0, nullable=False)
	realupvotes = Column(Integer, default=1)
	app_id=Column(Integer, ForeignKey("oauth_apps.id"))
	title = Column(String, nullable=False)
	title_html = Column(String, nullable=False)
	url = Column(String)
	body = Column(Text)
	body_html = Column(Text)
	flair = Column(String)
	embed_url = Column(String)
	task_id = Column(Integer, ForeignKey("tasks_repeatable_scheduled_submissions.id"))

	# Visibility states here
	state_user_deleted_utc = Column(DateTime(timezone=True), nullable=True) # null if it hasn't been deleted by the user
	state_mod = Column(Enum(StateMod), default=StateMod.FILTERED, nullable=False) # default to Filtered just to partially neuter possible exploits
	state_mod_set_by = Column(String, nullable=True) # This should *really* be a User.id, but I don't want to mess with the required refactoring at the moment - it's extra hard because it could potentially be a lot of extra either data or queries
	state_report = Column(Enum(StateReport), default=StateReport.UNREPORTED, nullable=False)

	Index('post_app_id_idx', app_id)
	Index('subimssion_binary_group_idx', state_mod, state_user_deleted_utc, over_18)
	Index('submission_state_mod_idx', state_mod)
	Index('submission_isdeleted_idx', state_user_deleted_utc)

	@declared_attr
	def submission_new_sort_idx(self):
		return Index('submission_new_sort_idx', self.state_mod, self.state_user_deleted_utc, self.created_utc.desc(), self.over_18)

	Index('submission_pinned_idx', is_pinned)
	Index('submissions_author_index', author_id)

	@declared_attr
	def submisission_created_utc_asc_idx(self):
		return Index('submissions_created_utc_asc_idx', self.created_utc.nulls_first())
	
	@declared_attr
	def submissions_created_utc_desc_idx(self):
		return Index('submissions_created_utc_desc_idx', self.created_utc.desc())

	Index('submissions_over18_index', over_18)

	author = relationship("User", primaryjoin="Submission.author_id==User.id")
	oauth_app = relationship("OauthApp", viewonly=True)
	reports = relationship("Flag", viewonly=True)
	comments = relationship("Comment", primaryjoin="Comment.parent_submission==Submission.id")
	notes = relationship("UserNote", back_populates="post")
	task = relationship("ScheduledSubmissionTask", back_populates="submissions")

	def submit(self, db: Session):
		from files.classes.user import User # imports this module
		# The author's own upvote counts unless they're shadowbanned
		shadowbanned = user_shadowbanned_locked(db, db.get(User, self.author_id))
		self.upvotes = self.realupvotes = 0 if shadowbanned else 1
		db.add(self)
		db.flush()

		vote = Vote(
			user_id=self.author_id, 
			vote_type=1,
			submission_id=self.id,
			real=not shadowbanned,
		)
		db.add(vote)

	def publish(self):
		'''
		Run when the post is offered to others: when it's submitted, a draft is published, or a moderator approves it. Notifies mentioned users and followers if others can see it; running again for an unchanged post notifies nobody twice.
		'''
		# this is absolutely horrifying. imports are very very tangled and the
		# spider web of imports is hard to maintain. we defer loading these
		# imports until as late as possible. otherwise there are import loops
		# that would require much more work to untangle
		from files.helpers.alerts import notify_submission_publish

		self.visibility_changed()
		if not self.private and not self.ghost and self.visibility_state.publicly_visible:
			notify_submission_publish(self)

	@hybrid_property
	def pinned(self) -> bool:
		'''Pinned to the top of the front page: pinned by an admin (`stickied` names them), and either without an expiry or not past it.'''
		return bool(self.stickied) and (self.stickied_utc is None or int(time.time()) <= self.stickied_utc)

	@pinned.expression
	def pinned(cls):
		return (cls.stickied != None) & ((cls.stickied_utc == None) | (cls.stickied_utc >= int(time.time())))

	def visibility_changed(self):
		'''Run whenever whether others can see the post may have changed: keeps the author's post count current.'''
		db = object_session(self)
		db.flush()
		self.author.post_count = db.query(Submission.id).filter_by(
			author_id=self.author_id,
			state_mod=StateMod.VISIBLE,
			state_user_deleted_utc=None,
			private=False).count()
		db.add(self.author)

	def __repr__(self):
		return f"<{self.__class__.__name__}(id={self.id})>"

	@property
	@lazy
	def should_hide_score(self):
		submission_age_hours = self.age_seconds / (60*60)
		return submission_age_hours < SCORE_HIDING_TIME_HOURS

	def votes_shown_to(self, v) -> tuple[int, int]:
		return votes_shown_to(self, v)

	@property
	@lazy
	def controversial(self):
		if self.downvotes > 5 and 0.25 < self.upvotes / self.downvotes < 4: return True
		return False

	@lazy
	def flags(self, v):
		flags = g.db.query(Flag).filter_by(post_id=self.id).order_by(Flag.created_datetimez).all()
		if not (v and (v.shadowbanned or v.admin_level >= 1)):
			for flag in flags:
				if flag.user.shadowbanned:
					flags.remove(flag)
		return flags

	@property
	def edited_string(self):
		return format_age(self.edited_utc) if self.edited_utc else "never"

	@property
	def edited_datetime(self):
		return format_datetime(self.edited_utc) if self.edited_utc else ""

	@property
	@lazy
	def score(self):
		return self.upvotes - self.downvotes

	@property
	@lazy
	def fullname(self):
		return f"post_{self.id}"	

	@property
	@lazy
	def shortlink(self):
		link = f"/post/{self.id}"

		output = title_regex.sub('', self.title.lower())
		output = output.split()[:6]
		output = '-'.join(output)

		if not output: output = '-'

		return f"{link}/{output}"

	@property
	@lazy
	def permalink(self):
		return SITE_FULL + self.shortlink

	@property
	@lazy
	def domain(self):
		if not self.url: return None
		if self.url.startswith('/'): return SITE
		domain = urlparse(self.url).netloc
		if domain.startswith("www."): domain = domain.split("www.")[1]
		return domain.replace("old.reddit.com", "reddit.com")

	@property
	@lazy
	def author_name(self):
		if self.ghost: return '👻'
		else: return self.author.username

	@property
	@lazy
	def is_youtube(self):
		return self.domain == "youtube.com" and self.embed_url and self.embed_url.startswith('<lite-youtube') 

	@property
	@lazy
	def thumb_url(self):
		if self.over_18:
			return SITE_FULL + assetcache_path('images/nsfw.webp')
		elif not self.url:
			return SITE_FULL + assetcache_path(f'images/{SITE_ID}/default_text.webp')
		elif self.thumburl: 
			if self.thumburl.startswith('/'):
				return SITE_FULL + self.thumburl
			return self.thumburl
		elif self.is_youtube or self.is_video:
			return SITE_FULL + assetcache_path('images/default_thumb_yt.webp')
		else:
			return SITE_FULL + assetcache_path('images/default_thumb_link.webp')

	@property
	@lazy
	def json_raw(self):
		data = {'author_name': self.author_name if self.author else '',
				'permalink': self.permalink,
				'shortlink': self.shortlink,
				'created_utc': self.created_utc,
				'id': self.id,
				'title': self.title,
				'is_nsfw': self.over_18,
				'is_bot': self.is_bot,
				'thumb_url': self.thumb_url,
				'domain': self.domain,
				'url': self.realurl(None),
				'body': self.body,
				'body_html': self.body_html,
				'created_utc': self.created_utc,
				'edited_utc': self.edited_utc or 0,
				'comment_count': self.comment_count,
				'stickied': self.stickied if self.pinned else None,
				'private' : self.private,
				'distinguish_level': self.distinguish_level,
				'voted': self.voted if hasattr(self, 'voted') else 0,
				}
		
		if not self.should_hide_score:
			data['score'] = self.score
			data['upvotes'] = self.upvotes
			data['downvotes'] = self.downvotes

		return data

	@property
	@lazy
	def json_core(self):
		if self.state_mod != StateMod.VISIBLE:
			return self.json_identity
		elif self.state_user_deleted_utc:
			return {
					'state_user_deleted_utc': self.state_user_deleted_utc,
					'id': self.id,
					'title': self.title,
					'permalink': self.permalink,
					}

		return self.json_raw

	@property
	@lazy
	def json(self):
		if self.state_user_deleted_utc or self.state_mod != StateMod.VISIBLE:
			return self.json_core
		return self.json_full

	def json_for(self, v):
		'''The post as `v` may see it: complete, or only its identity when it is hidden from them.'''
		if not self.visibility_state.is_visible_to(v): return self.json_identity
		data = dict(self.json_full)
		if "score" in data:
			data["upvotes"], data["downvotes"] = self.votes_shown_to(v)
			data["score"] = data["upvotes"] - data["downvotes"]
		if "replies" in self.__dict__: data["replies"] = [x.json_core_for(v) for x in self.replies if x.renders_for(v)]
		return data

	@property
	def json_identity(self):
		return {
			'state_user_deleted_utc': self.state_user_deleted_utc,
			'state_mod_set_by': self.state_mod_set_by,
			'id': self.id,
			'title': self.title,
			'permalink': self.permalink,
		}

	@property
	@lazy
	def json_full(self):
		data=self.json_raw

		data["author"]='👻' if self.ghost else self.author.json_core
		data["comment_count"]=self.comment_count

	
		if "voted" in self.__dict__:
			data["voted"] = self.voted

		return data

	@lazy
	def realurl(self, v):
		if self.url and self.url.startswith("https://old.reddit.com/"):

			url = self.url

			if '/comments/' in url and "sort=" not in url:
				if "?" in url: url += f"&context={RENDER_DEPTH_LIMIT}" 
				else: url += f"?context={RENDER_DEPTH_LIMIT - 1}"
			return url
		elif self.url:
			if self.url.startswith('/'): return SITE_FULL + self.url
			if not is_web_url(self.url): return ""
			return self.url
		else: return ""
 
	def realbody(self, v):
		return body_displayed(self, v, is_html=True)

	def plainbody(self, v):
		return body_displayed(self, v, is_html=False)

	@lazy
	def realtitle(self, v):
		return self.title_html if self.title_html else self.title

	@lazy
	def plaintitle(self, v):
		return self.title

	@property
	@lazy
	def is_video(self):
		return self.url and any((self.url.lower().endswith(x) for x in ('.mp4','.webm','.mov'))) and embed_fullmatch_regex.fullmatch(self.url)

	@property
	@lazy
	def is_image(self):
		if self.url and self.url.lower().endswith(IMAGE_URL_SUFFIXES) and (self.url.startswith('/') or self.url.startswith(f'{SITE_FULL}/') or embed_fullmatch_regex.fullmatch(self.url)):
			return True
		return False

	@lazy
	def active_flags(self, v): 
		return len(self.flags(v))
	
	@property
	def is_real_submission(self) -> bool:
		return True
	
	@property
	def edit_url(self) -> str:
		return f"/edit_post/{self.id}"
	
	def is_draft_hidden_from(self, v) -> bool:
		'''Drafts exist only for their author and moderators; to everyone else they aren't there at all.'''
		return self.private and not (v and (v.id == self.author_id or v.admin_level >= PERMS['POST_COMMENT_MODERATION']))

	@property
	def visibility_state(self) -> VisibilityState:
		return VisibilityState.from_submittable(self)
