import functools
from datetime import datetime, timezone

from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.sql.sqltypes import Boolean, Integer, String, Text

from files.classes.cron.tasks import (RepeatableTask, ScheduledTaskType,
                                      TaskRunContext)
from files.classes.submission import Submission
from files.classes.visstate import StateMod, StateReport, VisibilityState
from files.helpers.config.const import SUBMISSION_TITLE_LENGTH_MAXIMUM
from files.helpers.content import body_displayed
from files.helpers.lazy import lazy
from files.helpers.sanitize import filter_emojis_only

__all__ = ('ScheduledSubmissionTask',)


class ScheduledSubmissionTask(RepeatableTask):
	__tablename__ = "tasks_repeatable_scheduled_submissions"
	
	__mapper_args__ = {
		"polymorphic_identity": int(ScheduledTaskType.SCHEDULED_SUBMISSION),
	}

	id = Column(Integer, ForeignKey(RepeatableTask.id), primary_key=True)
	author_id_submission = Column(Integer, ForeignKey("users.id"), nullable=False)
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

	author = relationship("User", foreign_keys=author_id_submission)
	task = relationship(RepeatableTask)
	submissions = relationship(Submission,
		back_populates="task", order_by="Submission.id.desc()")

	def run_task(self, ctx:TaskRunContext) -> None:
		submission:Submission = self.make_submission(ctx)
		with ctx.app_context():
			# TODO: stop using app context (currently required for sanitize and
			# username pings)
			submission.submit(ctx.db) # TODO: thumbnails
			submission.publish()

	def make_submission(self, ctx:TaskRunContext) -> Submission:
		title:str = self.make_title(ctx.trigger_time)
		title_html:str = filter_emojis_only(title, graceful=True)
		if len(title_html) > 1500: raise ValueError("Rendered title too large")

		return Submission(
			created_utc=int(ctx.trigger_time.timestamp()),
			private=self.private,
			author_id=self.author_id_submission,
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
			state_mod=StateMod.VISIBLE,
			embed_url=self.embed_url,
			task_id=self.id,
		)
	
	def make_title(self, trigger_time:datetime) -> str:
		return trigger_time.strftime(self.title)
	
	# properties below here are mocked in order to reuse part of the submission
	# HTML template for previewing a submitted task

	@property
	def state_user_deleted_utc(self) -> datetime | None:
		return datetime.now(tz=timezone.utc) if not self.task.enabled else None

	@functools.cached_property
	def title_html(self) -> str:
		'''
		This is used as a mock property for display in submission listings that
		contain scheduled posts.

		.. warning::
		This property should not be used for generating the HTML for an actual
		submission as this will be missing the special formatting that may be
		applies to titles. Instead call 
		`ScheduledSubmissionContext.make_title()` with the `datetime` that the
		event was triggered at. 
		'''
		return filter_emojis_only(self.title)
	
	@property
	def author_name(self) -> str:
		return self.author.username

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
	def views(self) -> int:
		return 0
	
	@property
	def state_mod(self) -> StateMod:
		return StateMod.VISIBLE

	def award_count(self, kind):
		return 0

	@lazy
	def realurl(self, v):
		return Submission.realurl(self, v)
 
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
	def permalink(self):
		return f"/tasks/scheduled_posts/{self.id}"
	
	@property
	def shortlink(self):
		return self.permalink
	
	@property
	def is_real_submission(self) -> bool:
		return False
	
	@property
	def should_hide_score(self) -> bool:
		return True

	@property
	def edit_url(self) -> str:
		return f"/tasks/scheduled_posts/{self.id}/content"
	
	@property
	def visibility_state(self) -> VisibilityState:
		return VisibilityState(
			state_mod=StateMod.VISIBLE,
			state_mod_set_by=None,
			state_report=StateReport.UNREPORTED,
			deleted=False, # we only want to show deleted UI color if disabled
			op_shadowbanned=False,
			op_id=self.author_id_submission,
			op_name_safe=self.author_name
		)
