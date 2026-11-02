'''
In-process backend: drives the Python implementation directly, which also lets coverage measure it.

This is the only module in the spec tier that touches the application's code. Another backend (e.g. a real server driven over a socket, with test-mode control endpoints) would provide these same functions; everything else in the harness is implementation-neutral.
'''
import email
import smtplib
from io import BytesIO

import requests.adapters

from files.__main__ import app, db_session
from files.helpers import background
from files.tests import reset as _reset

_client = app.test_client(use_cookies=False)
_outbound_attempts: list[str] = []
_sent_mail: list[dict] = []


def request(method, path, *, headers, data=None, json=None, files=None):
	'''`files` maps field name to (filename, bytes, content type). Returns (status, [(header, value), ...], body bytes).'''
	if files:
		data = {**(data or {}), **{field: (BytesIO(content), filename, content_type) for field, (filename, content, content_type) in files.items()}}
	r = _client.open(path, method=method, headers=headers, data=data, json=json)
	return r.status_code, list(r.headers.items()), r.get_data()


def reset():
	# Release the app's thread-local session so an open transaction can't block the truncate
	db_session.remove()
	background.discard()
	_reset.reset()
	_outbound_attempts.clear()
	_sent_mail.clear()
	# Installed for the rest of the process; the legacy tests that would mind run before any spec test
	requests.adapters.HTTPAdapter.send = _blocked_http_send
	smtplib.SMTP = _CapturingSMTP
	smtplib.SMTP_SSL = _CapturingSMTP


def run_background_work():
	background.drain()


def sent_mail() -> list[dict]:
	return list(_sent_mail)


def take_outbound_attempts():
	attempts = list(_outbound_attempts)
	_outbound_attempts.clear()
	return attempts


def _blocked_http_send(self, request, *args, **kwargs):
	_outbound_attempts.append(f"HTTP {request.method} {request.url}")
	raise requests.exceptions.ConnectionError(f"Outbound HTTP is blocked in spec tests: {request.method} {request.url}")


class _CapturingSMTP:
	'''Stands in for an SMTP server connection, recording each message instead of delivering it.'''

	def __init__(self, host="", port=0, *args, **kwargs):
		pass

	def set_debuglevel(self, level):
		pass

	def starttls(self, *args, **kwargs):
		pass

	def login(self, user, password, *args, **kwargs):
		pass

	def sendmail(self, from_addr, to_addrs, msg, *args, **kwargs):
		_sent_mail.append({"from": from_addr, "to": list(to_addrs), "message": email.message_from_bytes(msg if isinstance(msg, bytes) else msg.encode())})
		return {}

	def quit(self):
		pass
