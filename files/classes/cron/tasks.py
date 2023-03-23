from __future__ import annotations

import contextlib
import dataclasses
from datetime import date, datetime, timedelta, timezone
from enum import IntEnum, IntFlag
from typing import TYPE_CHECKING, Any, Final, Optional, Union

import flask
import flask_caching
import flask_mail
import redis
from sqlalchemy.orm import relationship, scoped_session
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.sql.sqltypes import (Boolean, DateTime, Integer, SmallInteger,
                                     Text, Time)

from files.classes.base import CreatedBase
from files.helpers.time import format_age, format_datetime

if TYPE_CHECKING:
	from files.classes.user import User

class ScheduledTaskType(IntEnum):
	PYTHON_CALLABLE = 1
	SCHEDULED_SUBMISSION = 2

	def __str__(self):
		if not self.name: return super().__str__()
		return self.name.replace('_', ' ').title()


class ScheduledTaskState(IntEnum):
	WAITING = 1
	'''
	A task waiting to be triggered
	'''
	RUNNING = 2
	'''
	A task that is currently running
	'''


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

	NONE = 0 << 0
	ALL = WEEKDAYS | WEEKENDS

	@classmethod
	@property
	def all_days(cls) -> list["DayOfWeek"]:
		return [
			cls.SUNDAY, cls.MONDAY, cls.TUESDAY, cls.WEDNESDAY, 
	  		cls.THURSDAY, cls.FRIDAY, cls.SATURDAY
		]

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
		if not 0 <= weekday <= 6:
			raise Exception(
				f"Unexpected weekday value (got {weekday}, expected 0-6)")
		return _days[weekday] in self


_UserConvertible = Union["User", str, int]

@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class TaskRunContext:
	'''
	A full task run context, with references to all app globals embedded.
	This is the entirety of the application's global state at this point.

	This is explicit state. This is useful so scheduled tasks do not have 
	to import from  `files.__main__` and so they can use all of the features
	of the application without being in a request context.
	'''
	app:flask.app.Flask
	'''
	The application. Many of the app functions use the app context globals and 
	do not have their state explicitly passed. This is a convenience get out of
	jail free card so that most features (excepting those that require a 
	`request` context can be used.)
	'''
	cache:flask_caching.Cache
	'''
	A cache extension. This is useful for situations where a scheduled task
	might want to interact with the cache in some way (for example invalidating
	or adding something to the cache.)
	'''
	db:scoped_session
	'''
	A database session. Useful for when a task needs to modify something in the
	database (for example creating a submission)
	'''
	mail:flask_mail.Mail
	'''
	The mail extension. Needed for sending emails.
	'''
	redis:redis.Redis
	'''
	A direct reference to our redis connection. Normally most operations that
	involve the redis datastore use flask_caching's Cache object (accessed via 
	the `cache` property), however this is provided as a convenience for more 
	granular redis operations.
	'''
	task:RepeatableTask
	'''
	A reference to the task that is being ran.
	'''
	task_run:RepeatableTaskRun
	'''
	A reference to this current run of the task.
	'''
	trigger_time:datetime
	'''
	The date and time (UTC) that this task was triggered
	'''

	@property
	def run_time(self) -> datetime:
		'''
		The date and time (UTC) that this task was actually ran
		'''
		return self.task_run.created_datetime_py

	@contextlib.contextmanager
	def app_context(self, *, v:Optional[_UserConvertible]=None):
		'''
		Context manager that uses `self.app` to generate an app context and set
		up the application with expected globals. This assigns `g.db`, `g.v`, 
		and `g.debug`.
		
		This is intended for use with legacy code that does not pass state 
		explicitly and instead relies on the use of `g` for state passing. If
		at all possible, state should be passed explicitly to functions that
		require it.

		Usage is simple:
		```py
		with ctx.app_context() as app_ctx:
			# code that requires g
		```

		Any code that uses `g` can be ran here. As this is intended for
		scenarios that may be outside of a request context code that uses the
		request context may still raise `RuntimeException`s.

		An example

		```py
		from flask import g, request # import works ok

		def legacy_function():
			u:Optional[User] = g.db.get(User, 1784) # works ok! :)
			u.admin_level = \\
				request.values.get("admin_level", default=9001, type=int) 
				# raises a RuntimeError :(
			g.db.commit()
		```

		This is because there is no actual request being made. Creating a 
		mock request context is doable but outside of the scope of this 
		function as this is often not needed outside of route handlers (where
		this function is out of scope anyway).

		:param v: A `User`, an `int`, a `str`, or `None`. `g.v` will be set
		using the following rules:
		          
		1. If `v` is an `int`, `files.helpers.get_account` is called and the 
		result of that is stored in `g.v`.
		
		2. If `v` is an `str`, `files.helpers.get_user` is called and the 
		result of that is stored in `g.v`.
		
		3. If `v` is a `User`, it is stored in `g.v`.
			      
		It is expected that callees will provide a valid user ID or username.
		If an invalid one is provided, *no* exception will be raised and `g.v`
		will be set to `None`.

		This is mainly provided as an optional feature so that tasks can be 
		somewhat "sudo"ed as a particular user. Note that `g.v` is always 
		assigned (even if to `None`) in order to prevent code that depends on
		its existence from raising an exception.
		'''
		with self.app.app_context() as app_ctx:
			app_ctx.g.db = self.db

			from files.helpers.get import get_account, get_user

			if isinstance(v, str):
				v = get_user(v, graceful=True)
			elif isinstance(v, int):
				v = get_account(v, graceful=True, db=self.db)

			app_ctx.g.v = v
			app_ctx.g.debug = self.app.debug
			yield app_ctx

	@contextlib.contextmanager
	def db_transaction(self):
		try:
			yield
			self.db.commit()
		except:
			self.db.rollback()


_TABLE_NAME: Final[str] = "tasks_repeatable"


class RepeatableTask(CreatedBase):
	__tablename__ = _TABLE_NAME

	id = Column(Integer, primary_key=True, nullable=False)
	author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
	type_id = Column(SmallInteger, nullable=False)
	enabled = Column(Boolean, default=True, nullable=False)
	run_state = Column(SmallInteger, default=int(ScheduledTaskState.WAITING), nullable=False)
	run_time_last = Column(DateTime, default=None)
	
	frequency_day = Column(SmallInteger, nullable=False)
	time_of_day_utc = Column(Time, nullable=False)

	runs = relationship("RepeatableTaskRun", back_populates="task")

	@property
	def type(self) -> ScheduledTaskType:
		return ScheduledTaskType(self.type_id)
	
	@type.setter
	def type(self, value:ScheduledTaskType):
		self.type_id = value

	@property
	def frequency_day_flags(self) -> DayOfWeek:
		return DayOfWeek(self.frequency_day)
	
	@frequency_day_flags.setter
	def frequency_day_flags(self, value:DayOfWeek):
		self.frequency_day = int(value)
	
	@property
	def run_state_enum(self) -> ScheduledTaskState:
		return ScheduledTaskState(self.run_state)

	@run_state_enum.setter
	def run_state_enum(self, value:ScheduledTaskState):
		self.run_state = int(value)

	@property
	def run_time_last_or_created_utc(self) -> datetime:
		return self.run_time_last or self.created_datetime_py

	@property
	def run_time_last_str(self) -> str:
		if not self.run_time_last: return 'Never'
		return f'{format_datetime(self.run_time_last)} ' \
				f'({format_age(self.run_time_last)})'

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

	def run(self, db:scoped_session, trigger_time:datetime) -> RepeatableTaskRun:
		run:RepeatableTaskRun = RepeatableTaskRun(task_id=self.id)
		try:
			from files.__main__ import app, cache, mail, r  # i know
			ctx:TaskRunContext = TaskRunContext(
				app=app,
				cache=cache,
				db=db,
				mail=mail,
				redis=r,
				task=self,
				task_run=run,
				trigger_time=trigger_time,
			)
			self.run_task(ctx)
		except Exception as e:
			run.exception = e
		run.completed_utc = datetime.now(tz=timezone.utc)
		db.add(run)
		return run

	def run_task(self, ctx:TaskRunContext):
		raise NotImplementedError()

	def contains_day_str(self, day_str:str) -> bool:
		return bool(day_str) and \
			DayOfWeek[day_str.upper()] in self.frequency_day_flags

	def __repr__(self) -> str:
		return f'<{self.__class__.__name__}(id={self.id}, created_utc={self.created_date}, author_id={self.author_id})>'

	__mapper_args__ = {
		"polymorphic_on": type_id,
	}


class RepeatableTaskRun(CreatedBase):
	__tablename__ = "tasks_repeatable_runs"
	
	id = Column(Integer, primary_key=True)
	task_id = Column(Integer, ForeignKey(RepeatableTask.id), nullable=False)
	manual = Column(Boolean, default=False, nullable=False)
	traceback_str = Column(Text, nullable=True)

	completed_utc = Column(DateTime)

	task = relationship(RepeatableTask, back_populates="runs")

	exception: Optional[Exception] = None # not part of the db model

	@property
	def completed_datetime_py(self) -> datetime:
		return datetime.fromtimestamp(self.completed_utc, tz=timezone.utc)

	@property
	def completed_datetime_str(self) -> str:
		return format_datetime(self.completed_utc)

	@property
	def status_text(self) -> str:
		if not self.completed_utc: return "Running"
		return "Failed" if self.traceback_str else "Completed"

	@property
	def time_elapsed(self) -> Optional[timedelta]:
		if not self.completed_utc: return None
		return self.completed_datetime_py - self.created_datetime_py

	@property
	def time_elapsed_str(self) -> str:
		elapsed:Optional[timedelta] = self.time_elapsed
		if not elapsed: return ''
		return str(elapsed)

	def __setattr__(self, __name: str, __value: Any) -> None:
		if __name == "exception":
			self.exception = __value
			self.traceback_str = str(__value) if __value else None
		return super().__setattr__(__name, __value)
