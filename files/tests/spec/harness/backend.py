'''
In-process backend: drives the Python implementation directly, which also lets coverage measure it.

This is the only module in the spec tier that touches the application's code. Another backend (e.g. a real server driven over a socket, with test-mode control endpoints) would provide these same functions; everything else in the harness is implementation-neutral.
'''
import smtplib

import requests.adapters

from files.__main__ import app, db_session
from files.helpers import background
from files.tests import reset as _reset

_client = app.test_client(use_cookies=False)
_outbound_attempts: list[str] = []


def request(method, path, *, headers, data=None, json=None):
	'''Returns (status, [(header, value), ...], body bytes).'''
	r = _client.open(path, method=method, headers=headers, data=data, json=json)
	return r.status_code, list(r.headers.items()), r.get_data()


def reset():
	# Release the app's thread-local session so an open transaction can't block the truncate
	db_session.remove()
	background.discard()
	_reset.reset()
	_outbound_attempts.clear()
	# Installed for the rest of the process; the legacy tests that would mind run before any spec test
	requests.adapters.HTTPAdapter.send = _blocked_http_send
	smtplib.SMTP.connect = _blocked_smtp_connect


def run_background_work():
	background.drain()


def take_outbound_attempts():
	attempts = list(_outbound_attempts)
	_outbound_attempts.clear()
	return attempts


def _blocked_http_send(self, request, *args, **kwargs):
	_outbound_attempts.append(f"HTTP {request.method} {request.url}")
	raise requests.exceptions.ConnectionError(f"Outbound HTTP is blocked in spec tests: {request.method} {request.url}")


def _blocked_smtp_connect(self, host="localhost", port=0, *args, **kwargs):
	_outbound_attempts.append(f"SMTP {host}:{port}")
	raise ConnectionRefusedError(f"Outbound SMTP is blocked in spec tests: {host}:{port}")
