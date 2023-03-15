from os import environ
import re
import time
from typing import Literal, Optional
from urllib.parse import urlencode, urlparse, parse_qs
from flask import *
from sqlalchemy import *
from sqlalchemy.orm import relationship
from files.classes.base import Base
from files.__main__ import app
from files.classes.votes import CommentVote
from files.helpers.const import *
from files.helpers.content import moderated_body
from files.helpers.lazy import lazy
from .flags import CommentFlag
from random import randint
from .votes import CommentVote
from math import floor

CommentRenderContext = Literal['comments', 'volunteer']

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
	body = Column(Text)
	body_html = Column(Text, nullable=False)
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
		return f"<{self.__class__.__name__}(id={self.id})>"

	@property
	@lazy
	def should_hide_score(self):
		comment_age_seconds = int(time.time()) - self.created_utc
		comment_age_hours = comment_age_seconds / (60*60)
		return comment_age_hours < app.config['SCORE_HIDING_TIME_HOURS']
	
	def _score_context_str(self, score_type:Literal['score', 'upvotes', 'downvotes'], 
			context:CommentRenderContext) -> str:
		if self.is_message: return '' # don't show scores for messages
		if context == 'volunteer': return '' # volunteer: hide scores
		if self.should_hide_score: return '' # hide scores for new comments

		if score_type == 'upvotes': return str(self.upvotes)
		if score_type == 'score': return str(self.score)
		if score_type == 'downvotes': return str(self.downvotes)
		
	@lazy
	def upvotes_str(self, context:CommentRenderContext) -> str:
		return self._score_context_str('upvotes', context)
	
	@lazy
	def score_str(self, context:CommentRenderContext) -> str:
		return self._score_context_str('score', context)

	@lazy
	def downvotes_str(self, context:CommentRenderContext) -> str:
		return self._score_context_str('downvotes', context)

	@property
	@lazy
	def top_comment(self) -> Optional["Comment"]:
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
		moderated:Optional[str] = moderated_body(self, v)
		if moderated: return moderated
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
		moderated:Optional[str] = moderated_body(self, v)
		if moderated: return moderated
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
	def is_op(self): 
		return self.author_id == self.post.author_id
	
	@property
	@lazy
	def is_comment(self) -> bool:
		'''
		Returns whether this is an actual comment (i.e. not a private message)
		'''
		return bool(self.parent_submission)
	
	@property
	@lazy
	def is_message(self) -> bool:
		'''
		Returns whether this is a private message or modmail
		'''
		return not self.is_comment
	
	@property
	@lazy
	def is_strict_message(self) -> bool:
		'''
		Returns whether this is a private message or modmail
		but is not a notification
		'''
		return self.is_message and not self.is_notification
	
	@property
	@lazy
	def is_modmail(self) -> bool:
		'''
		Returns whether this is a modmail message
		'''
		if not self.is_message: return False
		if self.sentto == MODMAIL_ID: return True

		top_comment: Optional["Comment"] = self.top_comment
		return bool(top_comment.sentto == MODMAIL_ID)
	
	@property
	@lazy
	def is_notification(self) -> bool:
		'''
		Returns whether this is a notification
		'''
		return self.is_message and not self.sentto

	@lazy
	def header_msg(self, v, is_notification_page:bool, reply_count:int) -> str:
		'''
		Returns a message that is in the header for a comment, usually for
		display on a notification page.
		'''
		if self.post:
			post_html:str = f"<a href=\"{self.post.permalink}\">{self.post.realtitle(v)}</a>"
			if v:
				if v.id == self.author_id and reply_count:
					text = f"Comment {'Replies' if reply_count != 1 else 'Reply'}"
				elif v.id == self.post.author_id and self.level == 1:
					text = "Post Reply"
				elif self.parent_submission in v.subscribed_idlist():
					text = "Subscribed Thread"
				else:
					text = "Username Mention"
				if is_notification_page:
					return f"{text}: {post_html}"
			return post_html
		elif self.author_id in {AUTOJANNY_ID, NOTIFICATIONS_ID}:
			return "Notification"
		elif self.sentto == MODMAIL_ID:
			return "Sent to admins"
		else:
			return f"Sent to @{self.senttouser.username}"
		
	@lazy
	def voted_display(self, v) -> int:
		'''
		Returns data used to modify how to show the vote buttons.

		:returns: A number between `-2` and `1`. `-2` is returned if `v` is 
		`None`. `1` is returned if the user is the comment author.
		Otherwise, a value of `-1` (downvote),` 0` (no vote or no data), or `1`
		(upvote) is returned.
		'''
		if not v: return -2
		if v.id == self.author_id: return 1
		return getattr(self, 'voted', 0)
	
	@lazy
	def sticky_api_url(self, v) -> Optional[str]:
		'''
		Returns the API URL used to sticky this comment.
		:returns: Currently `None` always. Stickying comments was disabled
		UI-side on TheMotte.
		'''
		return None
		if not self.is_comment: return None
		if not v: return None
		if v.admin_level >= 2:
			return 'sticky_comment'
		if v.id == self.post.author_id:
			return 'pin_comment'
		if self.post.sub and v.mods(self.post.sub):
			return 'mod_pin'
		return None

	@lazy
	def active_flags(self, v): 
		return len(self.flags(v))
