import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import declarative_base, declared_attr
from sqlalchemy.schema import Column
from sqlalchemy.sql.sqltypes import Integer

from files.helpers.time import format_age

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
		return time.strftime("%d/%B/%Y %H:%M:%S UTC", time.gmtime(self.created_utc))
	
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
