from os import environ
import re
import time
from urllib.parse import urlencode, urlparse, parse_qs
from flask import *
from sqlalchemy import *
from sqlalchemy.orm import relationship
from files.__main__ import Base, app
from files.classes.votes import CommentVote
from files.helpers.const import *
from files.helpers.lazy import lazy
from .flags import CommentFlag
from random import randint
from .votes import CommentVote
from math import floor

class Comment(Base):

	__tablename__ = "comments"

	id = Column(Integer, primary_key=True)
	author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
	parent_submission = Column(Integer, ForeignKey("submissions.id"))
	created_utc = Column(Integer, nullable=False)
	edited_utc = Column(Integer, default=0, nullable=False)
	is_banned = Column(Boolean, default=False, nullable=False)
	ghost = Column(Boolean, default=False, nullable=False)
	bannedfor = Column(Boolean)
	distinguish_level = Column(Integer, default=0, nullable=False)
	deleted_utc = Column(Integer, default=0, nullable=False)
	is_approved = Column(Integer, ForeignKey("users.id"))
	level = Column(Integer, default=1, nullable=False)
	parent_comment_id = Column(Integer, ForeignKey("comments.id"))
	top_comment_id = Column(Integer)
	over_18 = Column(Boolean, default=False, nullable=False)
	is_bot = Column(Boolean, default=False, nullable=False)
	is_pinned = Column(String)
	is_pinned_utc = Column(Integer)
	sentto = Column(Integer, ForeignKey("users.id"))
	app_id = Column(Integer, ForeignKey("oauth_apps.id"))
	upvotes = Column(Integer, default=1, nullable=False)
	downvotes = Column(Integer, default=0, nullable=False)
	realupvotes = Column(Integer, default=1, nullable=False)
	descendant_count = Column(Integer, default=0, nullable=False)
	body = Column(String)
	body_html = Column(String)
	ban_reason = Column(String)
	filter_state = Column(String, nullable=False)

	Index('comment_parent_index', parent_comment_id)
	Index('comment_post_id_index', parent_submission)
	Index('comments_user_index', author_id)
	Index('fki_comment_approver_fkey', is_approved)
	Index('fki_comment_sentto_fkey', sentto)

	oauth_app = relationship("OauthApp", viewonly=True)
	post = relationship("Submission", viewonly=True)
	author = relationship("User", primaryjoin="User.id==Comment.author_id")
	senttouser = relationship("User", primaryjoin="User.id==Comment.sentto", viewonly=True)
	parent_comment = relationship("Comment", remote_side=[id], viewonly=True)
	parent_comment_writable = relationship("Comment", remote_side=[id])
	child_comments = relationship("Comment", lazy="dynamic", remote_side=[parent_comment_id], viewonly=True)
	awards = relationship("AwardRelationship",
		primaryjoin="AwardRelationship.comment_id == Comment.id",
		viewonly=True)
	reports = relationship("CommentFlag",
		primaryjoin="CommentFlag.comment_id == Comment.id",
		order_by="CommentFlag.created_utc",
		viewonly=True)
	notes = relationship("UserNote", back_populates="comment")
	
	def __init__(self, *args, **kwargs):
		if "created_utc" not in kwargs:
			kwargs["created_utc"] = int(time.time())
		if 'filter_state' not in kwargs:
			kwargs['filter_state'] = 'normal'
		super().__init__(*args, **kwargs)

	def __repr__(self):
		return f"<Comment(id={self.id})>"

	@property
	@lazy
	def should_hide_score(self):
		comment_age_seconds = int(time.time()) - self.created_utc
		comment_age_hours = comment_age_seconds / (60*60)
		return comment_age_hours < app.config['SCORE_HIDING_TIME_HOURS']

	@property
	@lazy
	def top_comment(self):
		return g.db.query(Comment).filter_by(id=self.top_comment_id).one_or_none()

	@lazy
	def flags(self, v):
		flags = self.reports
		if not (v and (v.shadowbanned or v.admin_level > 2)):
			for flag in flags:
				if flag.user.shadowbanned:
					flags.remove(flag)
		return flags

	@property
	@lazy
	def controversial(self):
		if self.downvotes > 5 and 0.25 < self.upvotes / self.downvotes < 4: return True
		return False

	@property
	@lazy
	def created_datetime(self):
		return time.strftime("%d/%B/%Y %H:%M:%S UTC", time.gmtime(self.created_utc))

	@property
	@lazy
	def age_string(self):
		notif_utc = self.__dict__.get("notif_utc")

		if notif_utc: 
			timestamp = notif_utc
		elif self.created_utc: 
			timestamp = self.created_utc
		else: 
			return None
		
		age = int(time.time()) - timestamp

		if age < 60:
			return "just now"
		elif age < 3600:
			minutes = int(age / 60)
			return f"{minutes}m ago"
		elif age < 86400:
			hours = int(age / 3600)
			return f"{hours}hr ago"
		elif age < 2678400:
			days = int(age / 86400)
			return f"{days}d ago"

		now = time.gmtime()
		ctd = time.gmtime(timestamp)

		months = now.tm_mon - ctd.tm_mon + 12 * (now.tm_year - ctd.tm_year)
		if now.tm_mday < ctd.tm_mday:
			months -= 1

		if months < 12:
			return f"{months}mo ago"
		else:
			years = int(months / 12)
			return f"{years}yr ago"

	@property
	@lazy
	def edited_string(self):

		age = int(time.time()) - self.edited_utc

		if age < 60:
			return "just now"
		elif age < 3600:
			minutes = int(age / 60)
			return f"{minutes}m ago"
		elif age < 86400:
			hours = int(age / 3600)
			return f"{hours}hr ago"
		elif age < 2678400:
			days = int(age / 86400)
			return f"{days}d ago"

		now = time.gmtime()
		ctd = time.gmtime(self.edited_utc)

		months = now.tm_mon - ctd.tm_mon + 12 * (now.tm_year - ctd.tm_year)
		if now.tm_mday < ctd.tm_mday:
			months -= 1

		if months < 12:
			return f"{months}mo ago"
		else:
			years = int(months / 12)
			return f"{years}yr ago"

	@property
	@lazy
	def score(self):
		return self.upvotes - self.downvotes

	@property
	@lazy
	def fullname(self):
		return f"t3_{self.id}"

	@property
	@lazy
	def parent(self):
		if not self.parent_submission: return None
		if self.level == 1: return self.post
		else: return g.db.get(Comment, self.parent_comment_id)

	@property
	@lazy
	def parent_fullname(self):
		if self.parent_comment_id: return f"t3_{self.parent_comment_id}"
		elif self.parent_submission: return f"t2_{self.parent_submission}"

	def replies(self, user):
		if self.replies2 != None: return [x for x in self.replies2 if not x.author.shadowbanned]
		author_id = None
		if user:
			author_id = user.id
		if not self.parent_submission:
			return sorted((x for x in self.child_comments
				if x.author
					and (x.filter_state not in ('filtered', 'removed') or x.author_id == author_id)
					and not x.author.shadowbanned),
				key=lambda x: x.created_utc)
		return sorted((x for x in self.child_comments
			if x.author
				and not x.author.shadowbanned
				and (x.filter_state not in ('filtered', 'removed') or x.author_id == author_id)),
			key=lambda x: x.created_utc, reverse=True)

	@property
	def replies_ignoring_shadowbans(self):
		if self.replies2 != None: return self.replies2
		if not self.parent_submission:
			return sorted(self.child_comments, key=lambda x: x.created_utc)
		return sorted(self.child_comments, key=lambda x: x.created_utc, reverse=True)

	@property
	def replies2(self):
		return self.__dict__.get("replies2")

	@replies2.setter
	def replies2(self, value):
		self.__dict__["replies2"] = value

	@property
	@lazy
	def shortlink(self):
		return f"{self.post.shortlink}/{self.id}?context=8#context"

	@property
	@lazy
	def permalink(self):
		return f"{SITE_FULL}{self.shortlink}"

	@property
	@lazy
	def morecomments(self):
		return f"{self.post.permalink}/{self.id}#context"

	@property
	@lazy
	def author_name(self):
		if self.ghost: return '👻'
		else: return self.author.username

	@property
	@lazy
	def json_raw(self):
		flags = {}
		for f in self.flags(None): flags[f.user.username] = f.reason

		data= {
			'id': self.id,
			'level': self.level,
			'author_name': self.author_name,
			'body': self.body,
			'body_html': self.body_html,
			'is_bot': self.is_bot,
			'created_utc': self.created_utc,
			'edited_utc': self.edited_utc or 0,
			'is_banned': bool(self.is_banned),
			'deleted_utc': self.deleted_utc,
			'is_nsfw': self.over_18,
			'permalink': f'/comment/{self.id}',
			'is_pinned': self.is_pinned,
			'distinguish_level': self.distinguish_level,
			'post_id': self.post.id if self.post else 0,
			'score': self.score,
			'upvotes': self.upvotes,
			'downvotes': self.downvotes,
			'is_bot': self.is_bot,
			'flags': flags,
			}

		if self.ban_reason:
			data["ban_reason"]=self.ban_reason

		return data

	def award_count(self, kind):
		if not FEATURES['AWARDS']: return 0
		return len([x for x in self.awards if x.kind == kind])

	@property
	@lazy
	def json_core(self):
		if self.is_banned:
			data = {'is_banned': True,
					'ban_reason': self.ban_reason,
					'id': self.id,
					'post': self.post.id if self.post else 0,
					'level': self.level,
					'parent': self.parent_fullname
					}
		elif self.deleted_utc:
			data = {'deleted_utc': self.deleted_utc,
					'id': self.id,
					'post': self.post.id if self.post else 0,
					'level': self.level,
					'parent': self.parent_fullname
					}
		else:
			data = self.json_raw
			if self.level >= 2: data['parent_comment_id']= self.parent_comment_id

		data['replies'] = [x.json_core for x in self.replies(None)]

		return data

	@property
	@lazy
	def json(self):
		data = self.json_core
		if self.deleted_utc or self.is_banned: return data
		data["author"] = '👻' if self.ghost else self.author.json_core
		data["post"] = self.post.json_core if self.post else ''
		return data

	def realbody(self, v):
		if self.post and self.post.club and not (v and (v.paid_dues or v.id in [self.author_id, self.post.author_id])): return f"<p>{CC} ONLY</p>"

		body = self.body_html or ""

		if body:

			if v:
				body = body.replace("old.reddit.com", v.reddit)

				if v.nitter and not '/i/' in body and '/retweets' not in body: body = body.replace("www.twitter.com", "nitter.net").replace("twitter.com", "nitter.net")

			if v and v.controversial:
				captured = []
				for i in controversial_regex.finditer(body):
					if i.group(0) in captured: continue
					captured.append(i.group(0))

					url = i.group(1)
					p = urlparse(url).query
					p = parse_qs(p)

					if 'sort' not in p: p['sort'] = ['controversial']

					url_noquery = url.split('?')[0]
					body = body.replace(url, f"{url_noquery}?{urlencode(p, True)}")

			if v and v.shadowbanned and v.id == self.author_id and 86400 > time.time() - self.created_utc > 60:
				ti = max(int((time.time() - self.created_utc)/60), 1)
				maxupvotes = min(ti, 13)
				rand = randint(0, maxupvotes)
				if self.upvotes < rand:
					amount = randint(0, 3)
					if amount == 1:
						self.upvotes += amount
						g.db.add(self)
						g.db.commit()

		return body

	def plainbody(self, v):
		if self.post and self.post.club and not (v and (v.paid_dues or v.id in [self.author_id, self.post.author_id])): return f"<p>{CC} ONLY</p>"
		body = self.body
		if not body: return ""
		return body

	@lazy
	def collapse_for_user(self, v, path):
		if v and self.author_id == v.id: return False

		if path == '/admin/removed/comments': return False

		if self.over_18 and not (v and v.over_18) and not (self.post and self.post.over_18): return True

		if self.is_banned: return True
			
		if v and v.filter_words and self.body and any(x in self.body for x in v.filter_words): return True
		
		return False

	@property
	@lazy
	def is_op(self): return self.author_id==self.post.author_id
	
	@lazy
	def active_flags(self, v): return len(self.flags(v))
