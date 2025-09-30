"""Tests for files/helpers/time.py utility functions."""

import time
from datetime import datetime, timedelta

from files.helpers.time import format_datetime, format_date, format_age


def test_format_datetime_with_int_timestamp():
	"""Test format_datetime with integer timestamp."""
	# January 1, 2020 00:00:00 UTC
	timestamp = 1577836800
	result = format_datetime(timestamp)
	assert result == "2020 January 01 00:00:00 UTC"


def test_format_datetime_with_float_timestamp():
	"""Test format_datetime with float timestamp."""
	timestamp = 1577836800.5
	result = format_datetime(timestamp)
	assert result == "2020 January 01 00:00:00 UTC"


def test_format_datetime_with_datetime():
	"""Test format_datetime with datetime object."""
	dt = datetime(2020, 1, 1, 0, 0, 0)
	result = format_datetime(dt)
	assert result == "2020 January 01 00:00:00 UTC"


def test_format_datetime_with_struct_time():
	"""Test format_datetime with struct_time."""
	st = time.strptime("2020 January 01 00:00:00", "%Y %B %d %H:%M:%S")
	result = format_datetime(st)
	assert result == "2020 January 01 00:00:00 UTC"


def test_format_datetime_with_none():
	"""Test format_datetime with None returns empty string."""
	result = format_datetime(None)
	assert result == ""


def test_format_date_with_int_timestamp():
	"""Test format_date with integer timestamp."""
	# January 1, 2020 00:00:00 UTC
	timestamp = 1577836800
	result = format_date(timestamp)
	assert result == "2020 January 01"


def test_format_date_with_float_timestamp():
	"""Test format_date with float timestamp."""
	timestamp = 1577836800.5
	result = format_date(timestamp)
	assert result == "2020 January 01"


def test_format_date_with_datetime():
	"""Test format_date with datetime object."""
	dt = datetime(2020, 1, 1, 12, 30, 45)
	result = format_date(dt)
	assert result == "2020 January 01"


def test_format_date_with_none():
	"""Test format_date with None returns empty string."""
	result = format_date(None)
	assert result == ""


def test_format_age_with_none():
	"""Test format_age with None returns empty string."""
	result = format_age(None)
	assert result == ""


def test_format_age_just_now():
	"""Test format_age for timestamps less than 60 seconds ago."""
	now = int(time.time())
	# 30 seconds ago
	timestamp = now - 30
	result = format_age(timestamp)
	assert result == "just now"


def test_format_age_minutes():
	"""Test format_age for timestamps in the minutes range."""
	now = int(time.time())
	# 5 minutes ago
	timestamp = now - (5 * 60)
	result = format_age(timestamp)
	assert result == "5m ago"

	# 45 minutes ago
	timestamp = now - (45 * 60)
	result = format_age(timestamp)
	assert result == "45m ago"


def test_format_age_hours():
	"""Test format_age for timestamps in the hours range."""
	now = int(time.time())
	# 2 hours ago
	timestamp = now - (2 * 3600)
	result = format_age(timestamp)
	assert result == "2hr ago"

	# 23 hours ago
	timestamp = now - (23 * 3600)
	result = format_age(timestamp)
	assert result == "23hr ago"


def test_format_age_days():
	"""Test format_age for timestamps in the days range."""
	now = int(time.time())
	# 5 days ago
	timestamp = now - (5 * 86400)
	result = format_age(timestamp)
	assert result == "5d ago"

	# 30 days ago
	timestamp = now - (30 * 86400)
	result = format_age(timestamp)
	assert result == "30d ago"


def test_format_age_months():
	"""Test format_age for timestamps in the months range."""
	now = int(time.time())
	# Approximately 3 months ago (90 days)
	timestamp = now - (90 * 86400)
	result = format_age(timestamp)
	assert "mo ago" in result

	# Approximately 6 months ago (180 days)
	timestamp = now - (180 * 86400)
	result = format_age(timestamp)
	assert "mo ago" in result


def test_format_age_years():
	"""Test format_age for timestamps in the years range."""
	now = int(time.time())
	# Approximately 2 years ago (730 days)
	timestamp = now - (730 * 86400)
	result = format_age(timestamp)
	assert "yr ago" in result

	# Approximately 5 years ago (1825 days)
	timestamp = now - (1825 * 86400)
	result = format_age(timestamp)
	assert "yr ago" in result


def test_format_age_with_datetime():
	"""Test format_age with datetime object."""
	now = datetime.utcnow()
	# 5 minutes ago
	past = now - timedelta(minutes=5)
	result = format_age(past)
	assert result == "5m ago"


def test_format_age_with_float_timestamp():
	"""Test format_age with float timestamp."""
	now = time.time()
	# 10 minutes ago
	timestamp = now - (10 * 60)
	result = format_age(timestamp)
	assert result == "10m ago"