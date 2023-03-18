import time
from datetime import datetime
from typing import Final, Union

DATE_FORMAT: Final[str] = '%Y %B %d'
DATETIME_FORMAT: Final[str] = '%Y %B %d %H:%M:%S UTC'

TimestampFormattable = Union[int, float, datetime, time.struct_time]

def format_datetime(timestamp:TimestampFormattable) -> str:
	return _format_timestamp(timestamp, DATETIME_FORMAT)

def format_date(timestamp:TimestampFormattable) -> str:
	return _format_timestamp(timestamp, DATE_FORMAT)

def _format_timestamp(timestamp:TimestampFormattable, format:str) -> str:
	if isinstance(timestamp, datetime):
		return timestamp.strftime(format)
	elif isinstance(timestamp, (int, float)):
		timestamp = time.gmtime(timestamp)
	elif not isinstance(timestamp, time.struct_time):
		raise TypeError("Invalid argument type (must be one of int, float, "
						"datettime, or struct_time)")
	return time.strftime(format, timestamp)
