from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from enum import IntEnum, IntFlag
from typing import Optional, Union

from flask import g
from sqlalchemy.orm import declared_attr, relationship, scoped_session
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.sql.sqltypes import (Boolean, Integer, SmallInteger, String,
                                     Text, Time)

from files.__main__ import app
from files.classes.base import CreatedBase
from files.classes.cron.submission import (ScheduledSubmission,
                                           ScheduledSubmissionContext)
from files.classes.submission import Submission


class ScheduledTaskType(IntEnum):
	SCHEDULED_SUBMISSION = 1


class DayOfWeek(IntFlag):
	SUNDAY = 1 << 1
	MONDAY = 1 << 2
	TUESDAY = 1 << 3
	WEDNESDAY = 1 << 4
	THURSDAY = 1 << 5
	FRIDAY = 1 << 6
	SATURDAY = 1 << 7

	WEEKDAYS = MONDAY | TUESDAY | WEDNESDAY | THURSDAY | FRIDAY
	WEEKENDS = SATURDAY | SUNDAY

	ALL = WEEKDAYS | WEEKENDS

	@property
	def empty(self) -> bool:
		return self not in self.ALL

	def __contains__(self, other:Union[date, "DayOfWeek"]) -> bool:
		_days:dict[int, "DayOfWeek"] = {
			0: self.MONDAY,
			1: self.TUESDAY,
			2: self.WEDNESDAY,
			3: self.THURSDAY,
			4: self.FRIDAY,
			5: self.SATURDAY,
			6: self.SUNDAY
		}
		if not isinstance(other, date):
			return super().__contains__(other)
		weekday:int = other.weekday()
		if not 6 <= weekday <= 0:
			raise Exception(
				f"Unexpected weekday value (got {weekday}, expected 0-6)")
		return _days[weekday] in self


class ScheduledTaskRun(CreatedBase):
	__tablename__ = "tasks_ran"
	
	id = Column(Integer, primary_key=True)
	task_id = Column(Integer, nullable=False)
	traceback_str = Column(Text, nullable=True)

	task = relationship("ScheduledTask")


class ScheduledTask(CreatedBase):
	__abstract__ = True

	@declared_attr
	def id(self):
		return Column(Integer, primary_key=True)
	
	@declared_attr
	def author_id(self):
		return Column(Integer, ForeignKey("users.id"), nullable=False)
	
	@declared_attr
	def type_id(self):
		return Column(String(64), nullable=False)
	
	@declared_attr
	def data_id(self):
		'''
		Generic pointer to some sort of data, dependent on the task type.
		For `ScheduledTaskType.SCHEDULED_SUBMISSION`, this is the 
		`ScheduledSubmission` id.
		'''
		return Column(Integer)

	@property
	def type(self) -> ScheduledTaskType:
		return ScheduledTaskType(self.type_id)
	
	@declared_attr
	def enabled(self):
		return Column(Boolean, default=True, nullable=False)
	
	def next_trigger(self, anchor:datetime) -> Optional[datetime]:
		raise NotImplementedError()
	
	def __repr__(self) -> str:
		return f'<{self.__class__.__name__}(id={self.id}, created_utc={self.created_date}, author_id={self.author_id})>'
	
	def run(self, db:scoped_session, trigger_time:datetime) -> ScheduledTaskRun:
		run:ScheduledTaskRun = ScheduledTaskRun(task_id=self.id)
		try:
			self._run_unwrapped(db, trigger_time)
		except Exception as e:
			run.traceback_str = str(e)
		return run

	def _run_unwrapped(self, db:scoped_session, trigger_time:datetime):
		if self.type != ScheduledTaskType.SCHEDULED_SUBMISSION:
			raise NotImplementedError("Scheduled task type not implemented")
		scheduled:ScheduledSubmission = db.get(ScheduledSubmission, self.data_id)
		submission:Submission = scheduled.make_submission(ScheduledSubmissionContext(trigger_time))
		submission.submit(db) # TODO: thumbnails
		with app.app_context(): # TODO: don't require app context (currently required for username pings)
			g.db = db
			submission.publish()

class RepeatableTask(ScheduledTask):
	__tablename__ = "tasks_repeatable"

	frequency_day = Column(SmallInteger, nullable=False)
	time_of_day_utc = Column(Time, nullable=False)

	@property
	def frequency_day_flags(self) -> DayOfWeek:
		return DayOfWeek(self.frequency)
	
	def next_trigger(self, anchor:datetime) -> Optional[datetime]:
		if not self.enabled: return None
		if self.frequency_day_flags.empty: return None

		day:timedelta = timedelta(1.0)
		target_date:datetime = anchor - day # incremented at start of for loop

		for i in range(8):
			target_date = target_date + day
			if i == 0 and target_date.time() > self.time_of_day_utc: continue
			if target_date in self.frequency_day_flags: break
		else:
			raise Exception("Could not find suitable timestamp to run next task")

		return datetime.combine(target_date, self.time_of_day_utc, tzinfo=timezone.utc) # type: ignore
