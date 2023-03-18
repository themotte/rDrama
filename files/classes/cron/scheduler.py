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
from sqlalchemy.ext.declarative import AbstractConcreteBase
from sqlalchemy.orm import declared_attr, relationship, scoped_session
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.sql.sqltypes import (Boolean, DateTime, Integer, SmallInteger,
                                     Text, Time)

from files.classes.base import CreatedBase

if TYPE_CHECKING:
	from files.classes.user import User

class ScheduledTaskType(IntEnum):
	PYTHON_CALLABLE = 1
	SCHEDULED_SUBMISSION = 2


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
	db:scoped_session
	mail:flask_mail.Mail
	redis:redis.Redis
	trigger_time:datetime

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
	def with_transaction(self):
		try:
			yield
			self.db.commit()
		except:
			self.db.rollback()

_TABLE_NAME: Final[str] = "tasks_scheduled"

class ScheduledTask(CreatedBase):
	__tablename__ = _TABLE_NAME
	@declared_attr
	def id(self):
		return Column(Integer, primary_key=True, nullable=False)
	
	@declared_attr
	def author_id(self):
		return Column(Integer, ForeignKey("users.id"), nullable=False)

	@declared_attr
	def type_id(self):
		return Column(SmallInteger, nullable=False)

	@property
	def type(self) -> ScheduledTaskType:
		return ScheduledTaskType(self.type_id)
	
	@declared_attr
	def enabled(self):
		return Column(Boolean, default=True, nullable=False)
	
	@declared_attr
	def last_run(self):
		return Column(DateTime, default=None)
	
	@property
	def last_run_or_created_utc(self) -> datetime:
		return self.last_run or self.created_datetime_py
	
	def next_trigger(self, anchor:datetime) -> Optional[datetime]:
		raise NotImplementedError()
	
	def __repr__(self) -> str:
		return f'<{self.__class__.__name__}(id={self.id}, created_utc={self.created_date}, author_id={self.author_id})>'
	
	__mapper_args__ = {
		"polymorphic_identity": _TABLE_NAME,
		"polymorphic_on": type_id,
	}


class RepeatableTask(ScheduledTask):
	__abstract__ = True

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
	
	def run(self, db:scoped_session, trigger_time:datetime) -> RepeatableTaskRun:
		run:RepeatableTaskRun = RepeatableTaskRun(task_id=self.id)
		try:
			from files.__main__ import app, cache, mail, r # i know
			ctx:TaskRunContext = TaskRunContext(
				app=app,
				cache=cache,
				db=db,
				mail=mail,
				redis=r,
				trigger_time=trigger_time,
			)
			self.run_task(ctx)
		except Exception as e:
			run.exception = e
		db.add(run)
		return run

	def run_task(self, ctx:TaskRunContext):
		raise NotImplementedError()


class RepeatableTaskRun(CreatedBase):
	__tablename__ = "tasks_repeatable_runs"
	
	id = Column(Integer, primary_key=True)
	task_id = Column(Integer, ForeignKey(RepeatableTask.id), nullable=False)
	manual = Column(Boolean, default=False, nullable=False)
	traceback_str = Column(Text, nullable=True)

	task = relationship(RepeatableTask)

	exception: Optional[Exception] = None # not part of the db model

	def __setattr__(self, __name: str, __value: Any) -> None:
		if __name == "exception":
			self.exception = __value
			self.traceback_str = str(__value) if __value else None
		return super().__setattr__(__name, __value)
