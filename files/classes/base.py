import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import declarative_base, declared_attr
from sqlalchemy.schema import Column
from sqlalchemy.sql.sqltypes import Integer, DateTime

from files.helpers.time import format_age, format_datetime

Base = declarative_base()


class CreatedBase(Base):
	__abstract__ = True
	
	def __init__(self, *args, **kwargs):
		if "created_utc" not in kwargs: 
			kwargs["created_utc"] = int(time.time())
		super().__init__(*args, **kwargs)
	
	@declared_attr
	def created_utc(self):
		return Column(Integer, nullable=False)
	
	@property
	def created_date(self) -> str:
		return self.created_datetime
	
	@property
	def created_datetime(self) -> str:
		return format_datetime(self.created_utc)
	
	@property
	def created_datetime_py(self) -> datetime:
		return datetime.fromtimestamp(self.created_utc, tz=timezone.utc)
	
	@property
	def age_seconds(self) -> int:
		return time.time() - self.created_utc
	
	@property
	def age_timedelta(self) -> timedelta:
		return datetime.now(tz=timezone.utc) - self.created_datetime_py

	@property
	def age_string(self) -> str:
		return format_age(self.created_utc)


class CreatedDateTimeBase(Base):
	"""
	An abstract class extending our default SQLAlchemy's `Base`.

	All classes inherit from this class automatically maps a `created_datetimez` column
	for the corresponding SQL table. This column will automatically record the created
	timestamp of rows. Retrieving `created_datetimez` will return a `datetime` object with 
	`tzinfo` of UTC.

	This class holds various convenience properties to get `created_datetimez` in different
	formats.
	"""
	__abstract__ = True

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
	
	@declared_attr
	def created_datetimez(self):
		"""
		Retrieving `created_datetimez` will return a `datetime` object with `tzinfo` for UTC.
		"""
		return Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

	@property
	def created_utc(self):
		"""
		the created date in UTC seconds. Milliseconds are truncated/rounded down.
		"""
		return int(self.created_datetimez.timestamp())
	
	@property
	def created_date(self) -> str:
		"""
		the created date in string.
		See `file.helpers.time.DATETIME_FORMAT` for the exact format
		Note: should this be using `format_date` and not `format_datetime`?
		"""
		return self.created_datetime
	
	@property
	def created_datetime(self) -> str:
		"""
		the created datetime in string.
		See `file.helpers.time.DATETIME_FORMAT` for the exact format.
		"""
		return format_datetime(self.created_datetimez)
	
	@property
	def created_datetime_py(self) -> datetime:
		"""
		the created datetime as a `datetime` object with `tzinfo` of UTC.
		"""
		return self.created_datetimez
	
	@property
	def age_seconds(self) -> int:
		"""
		number of seconds since created.
		"""
		return time.time() - self.created_utc
	
	@property
	def age_timedelta(self) -> timedelta:
		"""
		a `timedelta` object representing time since created.
		"""
		return datetime.now(tz=timezone.utc) - self.created_datetimez

	@property
	def age_string(self) -> str:
		"""
		a string representing time since created. Example: "1h ago", "2d ago".
		"""
		return format_age(self.created_datetimez)