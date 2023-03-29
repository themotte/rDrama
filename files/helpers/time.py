import calendar
import time
from datetime import datetime, timedelta
from typing import Final, Union

DATE_FORMAT: Final[str] = '%Y %B %d'
DATETIME_FORMAT: Final[str] = '%Y %B %d %H:%M:%S UTC'

AgeFormattable = Union[int, timedelta]
TimestampFormattable = Union[int, float, datetime, time.struct_time]

def format_datetime(timestamp: TimestampFormattable | None) -> str:
	return _format_timestamp(timestamp, DATETIME_FORMAT)


def format_date(timestamp: TimestampFormattable | None) -> str:
	return _format_timestamp(timestamp, DATE_FORMAT)


def format_age(timestamp: TimestampFormattable | None) -> str:
	if timestamp is None:
		return ""

	timestamp = _make_timestamp(timestamp)
	age:int = int(time.time()) - timestamp

	if age < 60: return "just now"
	if age < 3600:
		minutes = int(age / 60)
		return f"{minutes}m ago"
	if age < 86400:
		hours = int(age / 3600)
		return f"{hours}hr ago"
	if age < 2678400:
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


def _format_timestamp(timestamp: TimestampFormattable | None, format: str) -> str:
	if timestamp is None:
		return ""
	elif isinstance(timestamp, datetime):
		return timestamp.strftime(format)
	elif isinstance(timestamp, (int, float)):
		timestamp = time.gmtime(timestamp)
	elif not isinstance(timestamp, time.struct_time):
		raise TypeError("Invalid argument type (must be one of int, float, "
						"datettime, or struct_time)")
	return time.strftime(format, timestamp)


def _make_timestamp(timestamp: TimestampFormattable) -> int:
	if isinstance(timestamp, (int, float)):
		return int(timestamp)
	if isinstance(timestamp, datetime):
		return int(timestamp.timestamp())
	if isinstance(timestamp, time.struct_time):
		return calendar.timegm(timestamp)
