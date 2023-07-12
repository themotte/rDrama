from typing import TYPE_CHECKING, Literal, Optional
from urllib.parse import parse_qs, urlencode, urlparse

from flask import g
import math
from sqlalchemy import *
from sqlalchemy.orm import relationship

from files.classes.base import CreatedBase
from files.classes.visstate import StateMod, StateReport
from files.helpers.config.const import *
from files.helpers.config.environment import SCORE_HIDING_TIME_HOURS, SITE_FULL
from files.helpers.content import (ModerationState, body_displayed,
                                   execute_shadowbanned_fake_votes)
from files.helpers.lazy import lazy
from files.helpers.math import clamp
from files.helpers.time import format_age

if TYPE_CHECKING:
	from files.classes.user import User

CommentRenderContext = Literal['comments', 'volunteer']

class Comment(CreatedBase):
	__tablename__ = "comments"

	id = Column(Integer, primary_key=True)
	author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
	parent_submission = Column(Integer, ForeignKey("submissions.id"))
	edited_utc = Column(Integer, default=0, nullable=False)
	ghost = Column(Boolean, default=False, nullable=False)
	bannedfor = Column(Boolean)
	distinguish_level = Column(Integer, default=0, nullable=False)
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
	volunteer_janitor_badness = Column(Float, default=0.5, nullable=False)

	# Visibility states here
	state_user_deleted_utc = Column(DateTime(timezone=True), nullable=True) # null if it hasn't been deleted by the user
	state_mod = Column(Enum(StateMod), default=StateMod.FILTERED, nullable=False) # default to Filtered just to partially neuter possible exploits
	state_mod_set_by = Column(String, nullable=True) # This should *really* be a User.id, but I don't want to mess with the required refactoring at the moment - it's extra hard because it could potentially be a lot of extra either data or queries
	state_report = Column(Enum(StateReport), default=StateReport.UNREPORTED, nullable=False)

	Index('comment_parent_index', parent_comment_id)
	Index('comment_post_id_index', parent_submission)
	Index('comments_user_index', author_id)
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
		order_by="CommentFlag.created_timestampz",
		viewonly=True)
	notes = relationship("UserNote", back_populates="comment")

	def __repr__(self):
		return f"<{self.__class__.__name__}(id={self.id})>"

	@property
	@lazy
	def should_hide_score(self) -> bool:
		comment_age_hours = self.age_seconds / (60*60)
		return comment_age_hours < SCORE_HIDING_TIME_HOURS
	
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
		if not (v and (v.shadowbanned or v.admin_level >= 3)):
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
	def edited_string(self):
		if not self.edited_utc: return "never"
		return format_age(self.edited_utc)

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
					and (x.state_mod == StateMod.VISIBLE or x.author_id == author_id)
					and not x.author.shadowbanned),
				key=lambda x: x.created_utc)
		return sorted((x for x in self.child_comments
			if x.author
				and not x.author.shadowbanned
				and (x.state_mod == StateMod.VISIBLE or x.author_id == author_id)),
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
		if self.post:
			return f"{self.post.shortlink}/{self.id}?context=8#context"
		else:
			return f"/comment/{self.id}?context=8#context"

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

		return data

	def award_count(self, kind):
		if not FEATURES['AWARDS']: return 0
		return len([x for x in self.awards if x.kind == kind])

	@property
	@lazy
	def json_core(self):
		if self.state_mod != StateMod.VISIBLE:
			data = {
					'state_mod_set_by': self.state_mod_set_by,
					'id': self.id,
					'post': self.post.id if self.post else 0,
					'level': self.level,
					'parent': self.parent_fullname
				}
		elif self.state_user_deleted_utc:
			data = {
					'state_user_deleted_utc': self.state_user_deleted_utc,
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
		if self.state_user_deleted_utc or self.state_mod != StateMod.VISIBLE: return data
		data["author"] = '👻' if self.ghost else self.author.json_core
		data["post"] = self.post.json_core if self.post else ''
		return data

	def realbody(self, v):
		body = body_displayed(self, v, is_html=True)
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
		execute_shadowbanned_fake_votes(g.db, self, v) # TODO: put in route handler?
		return body

	def plainbody(self, v):
		return body_displayed(self, v, is_html=False)

	@lazy
	def collapse_for_user(self, v, path):
		if v and self.author_id == v.id: return False
		if path == '/admin/removed/comments': return False
		if self.over_18 and not (v and v.over_18) and not (self.post and self.post.over_18): return True
		# we no longer collapse removed things; the mods want to see them, non-mods see a placeholder anyway
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

	def sticky_api_url(self, v) -> str | None:
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
		elif v.id == self.post.author_id:
			return 'pin_comment'
		return None

	@lazy
	def active_flags(self, v): 
		return len(self.flags(v))

	@lazy
	def show_descendants(self, v:"User | None") -> bool:
		if self.moderation_state.is_visible_to(v, getattr(self, 'is_blocking', False)):
			return True
		return bool(self.descendant_count)

	@lazy
	def visibility_state(self, v:"User | None") -> tuple[bool, str]:
		'''
		Returns a tuple of whether this content is visible and a publicly 
		visible message to accompany it. The visibility state machine is
		a slight mess but... this should at least unify the state checks.
		'''
		return self.moderation_state.visibility_state(v, getattr(self, 'is_blocking', False))

	@property
	def moderation_state(self) -> ModerationState:
		return ModerationState.from_submittable(self)
	
	def volunteer_janitor_is_unknown(self):
		return self.volunteer_janitor_badness > 0.4 and self.volunteer_janitor_badness < 0.6

	def volunteer_janitor_is_bad(self):
		return self.volunteer_janitor_badness >= 0.6
	
	def volunteer_janitor_is_notbad(self):
		return self.volunteer_janitor_badness <= 0.4

	def volunteer_janitor_confidence(self):
		unitconfidence = (abs(self.volunteer_janitor_badness - 0.5) * 2)
		unitanticonfidence = 1 - unitconfidence
		logconfidence = -math.log(unitanticonfidence, 2)
		return round(logconfidence * 10)

	def volunteer_janitor_css(self):
		if self.volunteer_janitor_is_unknown():
			category = "unknown"
		elif self.volunteer_janitor_is_bad():
			category = "bad"
		elif self.volunteer_janitor_is_notbad():
			category = "notbad"
		
		strength = clamp(math.trunc(self.volunteer_janitor_confidence() / 10), 0, 3)

		return f"{category}_{strength}"
