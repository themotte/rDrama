import time
from urllib.parse import urlparse

from flask import g
from sqlalchemy import *
from sqlalchemy.orm import (declared_attr, deferred, relationship,
                            scoped_session)

from files.classes.base import CreatedBase
from files.classes.votes import Vote
from files.helpers.assetcache import assetcache_path
from files.helpers.config.const import *
from files.helpers.config.environment import (SCORE_HIDING_TIME_HOURS, SITE,
                                              SITE_FULL, SITE_ID)
from files.helpers.content import body_displayed
from files.helpers.lazy import lazy
from files.helpers.time import format_age

from .flags import Flag


class Submission(CreatedBase):
	__tablename__ = "submissions"

	id = Column(Integer, primary_key=True)
	author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
	edited_utc = Column(Integer, default=0, nullable=False)
	thumburl = Column(String)
	is_banned = Column(Boolean, default=False, nullable=False)
	bannedfor = Column(Boolean)
	ghost = Column(Boolean, default=False, nullable=False)
	views = Column(Integer, default=0, nullable=False)
	deleted_utc = Column(Integer, default=0, nullable=False)
	distinguish_level = Column(Integer, default=0, nullable=False)
	stickied = Column(String)
	stickied_utc = Column(Integer)
	sub = Column(String, ForeignKey("subs.name"))
	is_pinned = Column(Boolean, default=False, nullable=False)
	private = Column(Boolean, default=False, nullable=False)
	club = Column(Boolean, default=False, nullable=False)
	comment_count = Column(Integer, default=0, nullable=False)
	is_approved = Column(Integer, ForeignKey("users.id"))
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
	ban_reason = Column(String)
	embed_url = Column(String)
	filter_state = Column(String, nullable=False)
	task_id = Column(Integer, ForeignKey("tasks_repeatable_scheduled_submissions.id"))

	Index('fki_submissions_approver_fkey', is_approved)
	Index('post_app_id_idx', app_id)
	Index('subimssion_binary_group_idx', is_banned, deleted_utc, over_18)
	Index('submission_isbanned_idx', is_banned)
	Index('submission_isdeleted_idx', deleted_utc)

	@declared_attr
	def submission_new_sort_idx(self):
		return Index('submission_new_sort_idx', self.is_banned, self.deleted_utc, self.created_utc.desc(), self.over_18)

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
	approved_by = relationship("User", uselist=False, primaryjoin="Submission.is_approved==User.id", viewonly=True)
	awards = relationship("AwardRelationship", viewonly=True)
	reports = relationship("Flag", viewonly=True)
	comments = relationship("Comment", primaryjoin="Comment.parent_submission==Submission.id")
	subr = relationship("Sub", primaryjoin="foreign(Submission.sub)==remote(Sub.name)", viewonly=True)
	notes = relationship("UserNote", back_populates="post")
	task = relationship("ScheduledSubmissionTask", viewonly=True, back_populates="submissions")

	bump_utc = deferred(Column(Integer, server_default=FetchedValue()))

	def submit(self, db:scoped_session):
		# create submission...
		db.add(self)
		db.flush()
		
		# then create vote...
		vote = Vote(
			user_id=self.author_id, 
			vote_type=1,
			submission_id=self.id
		)
		db.add(vote)
		author = self.author
		author.post_count = db.query(Submission.id).filter_by(
			author_id=self.author_id, 
			is_banned=False, 
			deleted_utc=0).count()
		db.add(author)

	def publish(self):
		# this is absolutely horrifying. imports are very very tangled and the
		# spider web of imports is hard to maintain. we defer loading these
		# imports until as late as possible. otherwise there are import loops
		# that would require much more work to untangle
		from files.helpers.alerts import execute_username_mentions_submission
		from files.helpers.caching import invalidate_cache
		if self.private: return
		if not self.ghost: execute_username_mentions_submission(self)
		invalidate_cache(userpagelisting=True, changeloglist=\
			"[changelog]" in self.title.lower() or "(changelog)" in self.title.lower())

	def __repr__(self):
		return f"<{self.__class__.__name__}(id={self.id})>"

	@property
	@lazy
	def should_hide_score(self):
		submission_age_hours = self.age_seconds / (60*60)
		return submission_age_hours < SCORE_HIDING_TIME_HOURS

	@property
	@lazy
	def controversial(self):
		if self.downvotes > 5 and 0.25 < self.upvotes / self.downvotes < 4: return True
		return False

	@lazy
	def flags(self, v):
		flags = g.db.query(Flag).filter_by(post_id=self.id).order_by(Flag.created_utc).all()
		if not (v and (v.shadowbanned or v.admin_level > 2)):
			for flag in flags:
				if flag.user.shadowbanned:
					flags.remove(flag)
		return flags

	@property
	def edited_string(self):
		if not self.edited_utc: return "never"
		return format_age(int(time.time()) - self.edited_utc)

	@property
	@lazy
	def edited_datetime(self):
		return time.strftime("%d/%B/%Y %H:%M:%S UTC", time.gmtime(self.edited_utc))

	@property
	@lazy
	def score(self):
		return self.upvotes - self.downvotes

	@property
	@lazy
	def fullname(self):
		return f"t2_{self.id}"	

	@property
	@lazy
	def shortlink(self):
		link = f"/post/{self.id}"
		if self.sub: link = f"/h/{self.sub}{link}"

		if self.club: return link + '/-'

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
		flags = {}
		for f in self.flags(None): flags[f.user.username] = f.reason

		data = {'author_name': self.author_name if self.author else '',
				'permalink': self.permalink,
				'shortlink': self.shortlink,
				'is_banned': bool(self.is_banned),
				'deleted_utc': self.deleted_utc,
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
				'score': self.score,
				'upvotes': self.upvotes,
				'downvotes': self.downvotes,
				'stickied': self.stickied,
				'private' : self.private,
				'distinguish_level': self.distinguish_level,
				'voted': self.voted if hasattr(self, 'voted') else 0,
				'flags': flags,
				'club': self.club,
				}

		if self.ban_reason:
			data["ban_reason"]=self.ban_reason

		return data

	@property
	@lazy
	def json_core(self):
		if self.is_banned:
			return {'is_banned': True,
					'deleted_utc': self.deleted_utc,
					'ban_reason': self.ban_reason,
					'id': self.id,
					'title': self.title,
					'permalink': self.permalink,
					}
		elif self.deleted_utc:
			return {'is_banned': bool(self.is_banned),
					'deleted_utc': True,
					'id': self.id,
					'title': self.title,
					'permalink': self.permalink,
					}

		return self.json_raw

	@property
	@lazy
	def json(self):
		data=self.json_core
		
		if self.deleted_utc or self.is_banned:
			return data

		data["author"]='👻' if self.ghost else self.author.json_core
		data["comment_count"]=self.comment_count

	
		if "replies" in self.__dict__:
			data["replies"]=[x.json_core for x in self.replies]

		if "voted" in self.__dict__:
			data["voted"] = self.voted

		return data

	def award_count(self, kind):
		if not FEATURES['AWARDS']: return 0
		return len([x for x in self.awards if x.kind == kind])

	@lazy
	def realurl(self, v):
		if v and self.url and self.url.startswith("https://old.reddit.com/"):

			url = self.url.replace("old.reddit.com", v.reddit)

			if '/comments/' in url and "sort=" not in url:
				if "?" in url: url += f"&context={RENDER_DEPTH_LIMIT}" 
				else: url += f"?context={RENDER_DEPTH_LIMIT - 1}"
				if v.controversial: url += "&sort=controversial"
			return url
		elif self.url:
			if v and v.nitter and '/i/' not in self.url and '/retweets' not in self.url: return self.url.replace("www.twitter.com", "nitter.net").replace("twitter.com", "nitter.net")
			if self.url.startswith('/'): return SITE_FULL + self.url
			return self.url
		else: return ""
 
	def realbody(self, v):
		return body_displayed(self, v, True)

	def plainbody(self, v):
		return body_displayed(self, v, False)

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
		if self.url and (self.url.lower().endswith('.webp') or self.url.lower().endswith('.jpg') or self.url.lower().endswith('.png') or self.url.lower().endswith('.gif') or self.url.lower().endswith('.jpeg') or self.url.lower().endswith('?maxwidth=9999') or self.url.lower().endswith('&fidelity=high')) and (self.url.startswith('/') or self.url.startswith(f'{SITE_FULL}/') or embed_fullmatch_regex.fullmatch(self.url)):
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
