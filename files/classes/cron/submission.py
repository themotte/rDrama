import functools
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.sql.sqltypes import (Boolean, Integer, String,
                                     Text)
from files.classes.base import CreatedBase

from files.classes.cron.scheduler import ScheduledTask
from files.classes.submission import Submission
from files.helpers.const import (RENDER_DEPTH_LIMIT, SITE_FULL,
                                 SUBMISSION_TITLE_LENGTH_MAXIMUM)
from files.helpers.content import body_displayed
from files.helpers.lazy import lazy
from files.helpers.sanitize import filter_emojis_only

@dataclass(frozen=True, slots=True)
class ScheduledSubmissionContext:
	time: datetime

	def make_title(self, title_template:str) -> str:
		return self.time.strftime(title_template)


class ScheduledSubmission(CreatedBase):
	__tablename__ = "submissions_scheduled"

	id = Column(Integer, primary_key=True, nullable=False)
	author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
	ghost = Column(Boolean, default=False, nullable=False)
	private = Column(Boolean, default=False, nullable=False)
	over_18 = Column(Boolean, default=False, nullable=False)
	is_bot = Column(Boolean, default=False, nullable=False)
	title = Column(String(SUBMISSION_TITLE_LENGTH_MAXIMUM), nullable=False)
	url = Column(String)
	body = Column(Text)
	body_html = Column(Text)
	flair = Column(String)
	embed_url = Column(String)

	task_id = Column(Integer, ForeignKey(ScheduledTask.id), nullable=False)

	task = relationship(ScheduledTask)

	def make_submission(self, ctx:ScheduledSubmissionContext) -> Submission:
		title:str = ctx.make_title(self.title)
		title_html:str = filter_emojis_only(title, graceful=True)
		if len(title_html) > 1500: raise ValueError("Rendered title too large")

		return Submission(
			created_utc=int(ctx.time.timestamp()),
			private=self.private,
			author_id=self.author_id,
			over_18=self.over_18,
			app_id=None,
			is_bot =self.is_bot,
			title=title,
			title_html=title_html,
			url=self.url,
			body=self.body,
			body_html=self.body_html,
			flair=self.flair,
			ghost=self.ghost,
			filter_state='normal',
			embed_url=self.embed_url,
		)
	
	# properties below here are mocked in order to reuse part of the submission
	# HTML template for previewing a submitted task

	@functools.cached_property
	def title_html(self) -> str:
		'''
		Do not use this for getting the HTML. Instead call 
		`ScheduledSubmissionContext.make_title()`
		'''
		return filter_emojis_only(self.title)

	@property
	def upvotes(self) -> int:
		return 1
	
	@property
	def score(self) -> int:
		return 1
	
	@property
	def downvotes(self) -> int:
		return 0

	@property
	def realupvotes(self) -> int:
		return 1
	
	@property
	def comment_count(self) -> int:
		return 0
	
	@property
	def filter_state(self) -> str:
		return 'normal'

	def award_count(self, kind):
		return 0

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
			if v and v.nitter and '/i/' not in self.url and '/retweets' not in self.url: 
				return self.url.replace("www.twitter.com", "nitter.net").replace("twitter.com", "nitter.net")
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