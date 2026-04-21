import io
import re
from contextlib import redirect_stderr

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from files import __main__ as main
from files.__main__ import LazyLoadReporter, db_session
from files.classes import Submission, User

from . import util_accounts, util

pytestmark = pytest.mark.filterwarnings(
	"ignore::files.tests.conftest.LazyLoadWarning"
)


def _trigger_lazy_load():
	"""Create a fresh submission, reload it from the session, then access
	.author after expiring that relationship to force a lazy load."""
	client, _ = util_accounts.create_test_client_and_user()
	response, _ = util.post_with_formkey(
		client, "/submit",
		data={"title": util.generate_text(), "body": util.generate_text()},
	)
	assert response.status_code == 200

	post = util.ItemData.from_html(response.text)
	db_session.expunge_all()
	sub = db_session.get(Submission, post.id)
	db_session.expire(sub, ['author'])
	_ = sub.author


def _set_global_reporter_enabled(enabled: bool):
	"""Temporarily disable the app-level reporter so tests only observe
	the reporter instance they register themselves."""
	reporter = getattr(main, "_lazy_load_reporter", None)
	if reporter is None:
		return None

	listener = reporter.on_orm_execute
	is_registered = event.contains(Session, "do_orm_execute", listener)
	if enabled and not is_registered:
		event.listen(Session, "do_orm_execute", listener)
	elif not enabled and is_registered:
		event.remove(Session, "do_orm_execute", listener)

	return is_registered


def test_reports_lazy_load_with_field_name():
	"""The reporter should emit a message identifying the class and
	relationship that triggered the lazy load."""
	reporter = LazyLoadReporter(interval=0)
	listener = reporter.on_orm_execute
	event.listen(Session, "do_orm_execute", listener)
	global_reporter_was_enabled = _set_global_reporter_enabled(False)
	try:
		buf = io.StringIO()
		with redirect_stderr(buf):
			_trigger_lazy_load()
		output = buf.getvalue()
		assert "[lazy-load]" in output
		# Should have reported at least one lazy load with Class.field format
		assert re.search(r"\[lazy-load\] \w+\.\w+", output), \
			f"Expected Class.field format in: {output}"
	finally:
		if global_reporter_was_enabled:
			_set_global_reporter_enabled(True)
		event.remove(Session, "do_orm_execute", listener)


def test_suppresses_within_interval():
	"""Lazy loads within the interval window should be counted, not
	reported individually."""
	reporter = LazyLoadReporter(interval=9999)
	listener = reporter.on_orm_execute
	event.listen(Session, "do_orm_execute", listener)
	global_reporter_was_enabled = _set_global_reporter_enabled(False)
	try:
		buf = io.StringIO()
		with redirect_stderr(buf):
			# First one gets reported (last_report starts at 0)
			_trigger_lazy_load()
			# Second one should be suppressed
			_trigger_lazy_load()
		output = buf.getvalue()
		lines = [l for l in output.strip().splitlines() if "[lazy-load]" in l]
		assert len(lines) == 1, f"Expected 1 report, got {len(lines)}: {lines}"
		assert reporter._suppressed >= 1
	finally:
		if global_reporter_was_enabled:
			_set_global_reporter_enabled(True)
		event.remove(Session, "do_orm_execute", listener)


def test_reports_suppressed_count():
	"""After the interval elapses, the next report should include the
	suppressed count."""
	reporter = LazyLoadReporter(interval=0)
	listener = reporter.on_orm_execute
	event.listen(Session, "do_orm_execute", listener)
	global_reporter_was_enabled = _set_global_reporter_enabled(False)
	try:
		# First: fill up suppressed count by using a long interval
		reporter.interval = 9999
		_trigger_lazy_load()  # reported (first ever)
		_trigger_lazy_load()  # suppressed
		_trigger_lazy_load()  # suppressed

		# Now drop the interval and capture the next report
		reporter.interval = 0
		buf = io.StringIO()
		with redirect_stderr(buf):
			_trigger_lazy_load()
		output = buf.getvalue()
		assert "unreported since last" in output
	finally:
		if global_reporter_was_enabled:
			_set_global_reporter_enabled(True)
		event.remove(Session, "do_orm_execute", listener)
