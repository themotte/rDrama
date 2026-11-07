import math
from typing import TYPE_CHECKING, Literal, Optional

from flask import g
from sqlalchemy import *
from sqlalchemy.orm import relationship

from files.classes.base import CreatedBase
from files.classes.notifications import Notification
from files.classes.votes import votes_shown_to
from files.classes.visstate import StateMod, StateReport, VisibilityState
from files.helpers.config.const import *
from files.helpers.config.environment import SCORE_HIDING_TIME_HOURS, SITE_FULL
from files.helpers.content import body_displayed
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
	Index('comment_top_comment_id_index', top_comment_id)

	oauth_app = relationship("OauthApp", viewonly=True)
	post = relationship("Submission", viewonly=True)
	author = relationship("User", primaryjoin="User.id==Comment.author_id")
	senttouser = relationship("User", primaryjoin="User.id==Comment.sentto", viewonly=True)
	parent_comment = relationship("Comment", remote_side=[id], viewonly=True)
	child_comments = relationship("Comment", lazy="dynamic", remote_side=[parent_comment_id], viewonly=True)
	reports = relationship("CommentFlag",
		primaryjoin="CommentFlag.comment_id == Comment.id",
		order_by="CommentFlag.created_datetimez",
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
			context:CommentRenderContext, v:Optional["User"]) -> str:
		if self.is_message: return '' # don't show scores for messages
		if context == 'volunteer': return '' # volunteer: hide scores
		if self.should_hide_score: return '' # hide scores for new comments

		ups, downs = self.votes_shown_to(v)
		if score_type == 'upvotes': return str(ups)
		if score_type == 'score': return str(ups - downs)
		if score_type == 'downvotes': return str(downs)

	def upvotes_str(self, context:CommentRenderContext, v:Optional["User"]) -> str:
		return self._score_context_str('upvotes', context, v)

	def score_str(self, context:CommentRenderContext, v:Optional["User"]) -> str:
		return self._score_context_str('score', context, v)

	def downvotes_str(self, context:CommentRenderContext, v:Optional["User"]) -> str:
		return self._score_context_str('downvotes', context, v)

	def votes_shown_to(self, v:Optional["User"]) -> tuple[int, int]:
		return votes_shown_to(self, v)

	@lazy
	def flags(self, v):
		flags = self.reports
		if not (v and (v.shadowbanned or v.admin_level >= 1)):
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
		return f"comment_{self.id}"

	@property
	@lazy
	def parent(self):
		if not self.parent_submission: return None
		if self.level == 1: return self.post
		else: return g.db.get(Comment, self.parent_comment_id)

	@property
	@lazy
	def parent_fullname(self):
		if self.parent_comment_id: return f"comment_{self.parent_comment_id}"
		elif self.parent_submission: return f"post_{self.parent_submission}"

	def replies(self, user):
		if self.replies2 != None: return [x for x in self.replies2 if x.renders_for(user)]
		author_id = None
		if user:
			author_id = user.id
		if not self.parent_submission:
			return sorted((x for x in self.child_comments
				if x.author
					and (x.state_mod == StateMod.VISIBLE or x.author_id == author_id)
					and not x.author.shadowbanned),
				key=lambda x: x.created_utc)
		return sorted((x for x in self.child_comments if x.renders_for(user)), key=lambda x: x.created_utc, reverse=True)

	def shadowban_hides_from(self, v) -> bool:
		'''Whether its author's shadowban hides the comment from `v`: everyone but the author and admins (level 2+).'''
		return bool(self.author.shadowbanned) and not (v and (v.id == self.author_id or v.admin_level >= PERMS['USER_SHADOWBAN']))

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
			'is_bot': self.is_bot,
			}
		
		if not self.should_hide_score:
			data['score'] = self.score
			data['upvotes'] = self.upvotes
			data['downvotes'] = self.downvotes

		return data

	@property
	def json_place(self) -> dict:
		'''Where the comment sits, without anything of its own: what its JSON holds when it's hidden.'''
		return {
			'id': self.id,
			'post': self.post.id if self.post else 0,
			'level': self.level,
			'parent': self.parent_fullname,
		}

	def json_core_for(self, v:Optional["User"], *, without_replies:bool=False) -> dict:
		'''The comment as `v` may see it, without its author and post: whole, or a stub (its place in the thread and why it's hidden) when it's hidden from them.'''
		if self.visibility_state.is_visible_to(v):
			data = dict(self.json_raw)
			if 'score' in data:
				data['upvotes'], data['downvotes'] = self.votes_shown_to(v)
				data['score'] = data['upvotes'] - data['downvotes']
			if self.level >= 2: data['parent_comment_id'] = self.parent_comment_id
		else:
			data = self.json_place
			# Why it's hidden, as the page says: hidden by its author's shadowban, it reads as removed by no one
			if self.state_mod == StateMod.REMOVED: data['state_mod_set_by'] = self.state_mod_set_by
			elif self.shadowban_hides_from(v): data['state_mod_set_by'] = None
			elif self.state_mod != StateMod.VISIBLE: data['state_mod_set_by'] = self.state_mod_set_by
			elif self.state_user_deleted_utc: data['state_user_deleted_utc'] = self.state_user_deleted_utc
		data['replies'] = [] if without_replies else [x.json_core_for(v) for x in self.replies(v)]
		return data

	def json_for(self, v:Optional["User"], *, without_replies:bool=False) -> dict:
		'''The comment as `v` may see it, with its author and its post (without the post's replies) when it isn't hidden from them. Listings leave out its replies (`without_replies`).'''
		data = self.json_core_for(v, without_replies=without_replies)
		if self.visibility_state.is_visible_to(v):
			data['author'] = '👻' if self.ghost else self.author.json_core
			data['post'] = {key: value for key, value in self.post.json_for(v).items() if key != 'replies'} if self.post else ''
		return data

	def realbody(self, v):
		return body_displayed(self, v, is_html=True)

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

	def is_open_to(self, v:Optional["User"]) -> bool:
		'''Whether `v` may open this comment at all: a private message only by its sender, its recipient, those taking part in its conversation and admins (level 2+); one of the site's notices by those it notified and admins; a comment on a post by whoever may see the post.'''
		if self.parent_submission: return not self.post.is_draft_hidden_from(v)
		if not v: return False
		if v.id in (self.author_id, self.sentto) or self.takes_part_in_thread(v) or v.admin_level >= PERMS['POST_COMMENT_MODERATION']: return True
		return self.is_notification and g.db.query(exists().where(Notification.comment_id == self.id, Notification.user_id == v.id)).scalar()

	@property
	@lazy
	def thread_top(self) -> Optional["Comment"]:
		'''The first message of the conversation this message is in, or None when it's in none: a comment on a post, a notice, or a message older versions left outside any conversation (under a comment on a post, under a notice, or pointing at a first message that's missing or isn't one).'''
		if self.parent_submission: return None
		# From the session when the thread is loaded
		top = self if self.top_comment_id == self.id else g.db.get(Comment, self.top_comment_id) if self.top_comment_id else None
		if not top or top.parent_submission or top.sentto is None or top.parent_comment_id: return None
		return top

	def takes_part_in_thread(self, v:Optional["User"]) -> bool:
		'''Whether `v` takes part in this message's conversation: its two users in a direct thread; its starter and admins from level 2 in a modmail thread.'''
		top = self.thread_top
		if not (top and v): return False
		if v.id == top.author_id: return True
		if top.sentto == MODMAIL_ID: return v.admin_level >= PERMS['POST_COMMENT_MODERATION']
		return v.id == top.sentto

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
	def is_notification(self) -> bool:
		'''
		Returns whether this is a notification
		'''
		return self.is_message and not self.sentto

	@lazy
	def header_msg(self, v, is_notification_page: bool) -> str:
		'''
		Returns a message that is in the header for a comment, usually for
		display on a notification page.
		'''
		if self.post:
			post_html:str = f"<a href=\"{self.post.permalink}\">{self.post.realtitle(v)}</a>"
			if v:
				if self.level > 1 and v.id == self.parent_comment.author_id:
					text = "Comment Reply"
				elif self.level == 1 and v.id == self.post.author_id:
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
		elif self.senttouser is not None:
			return f"Sent to @{self.senttouser.username}"
		else:
			# This shouldn't actually be possible.
			return ""
		
	@lazy
	def voted_display(self, v) -> int:
		'''
		Returns data used to modify how to show the vote buttons.

		:returns: A number between `-2` and `1`. `-2` is returned if `v` is 
		`None`. Otherwise, a value of `-1` (downvote),` 0` (no vote or no data), or `1`
		(upvote) is returned.
		'''
		if not v: return -2
		return getattr(self, 'voted', 0)

	@lazy
	def active_flags(self, v): 
		return len(self.flags(v))

	def renders_for(self, v:"User | None") -> bool:
		'''Whether the comment shows to `v` at all: whole when they may see it, else as a placeholder holding replies they may see. Judged from the loaded thread; where the thread wasn't loaded below the comment, from its count of counted descendants.'''
		# Remembered per viewer: rendering asks again at every level of the thread
		answers = self.__dict__.setdefault("_renders_for", {})
		key = v.id if v else None
		if key not in answers:
			if self.visibility_state.is_visible_to(v): answers[key] = True
			elif self.replies2: answers[key] = any(reply.renders_for(v) for reply in self.replies2)
			else: answers[key] = bool(self.descendant_count)
		return answers[key]

	@lazy
	def visibility_and_message(self, v:"User | None") -> tuple[bool, str | None]:
		return self.visibility_state.visibility_and_message(v)

	@property
	def visibility_state(self) -> VisibilityState:
		return VisibilityState.from_submittable(self)
	
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
