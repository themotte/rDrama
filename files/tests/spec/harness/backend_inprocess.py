'''
In-process backend: drives the Python implementation directly, which also lets coverage measure it, and its in-process checks (route coverage, what pages offer) watch it.

This is the only module in the spec tier that touches the application's code. backend_process provides the same functions (__all__) for an implementation running in its own processes; everything else in the harness is implementation-neutral.
'''
import email
import smtplib
import time
from io import BytesIO

import requests.adapters
import urllib3

from files.__main__ import app, db_session, db_session_factory, limiter
import files.cli  # registers the command-line commands
from files.commands.cron import tasks_run_due
from files.helpers import background
from files.helpers.strings import bool_from_string
from files.tests import reset as _reset
from files.tests.spec.harness import config
from files.tests.spec.harness.process_proxy import key as external_key

__all__ = ["request", "reset", "run_background_work", "limit_clock_set", "cli", "run_scheduler", "sent_mail", "take_outbound_attempts", "take_server_log", "external_serve", "external_unreachable", "external_requests"]

_client = app.test_client(use_cookies=False)
_outbound_attempts: list[str] = []
_sent_mail: list[dict] = []
_UNREACHABLE = object()
_external_responses: dict[tuple, object] = {}
_external_requests: list[dict] = []


def request(method, target, headers, body, peer):
	'''Sends a request (`target` as on the request line, `body` encoded as `headers` say) from address `peer`. Returns (status, [(header, value), ...], body bytes).'''
	r = _client.open(target, method=method, headers=headers, data=body or None, environ_overrides={"REMOTE_ADDR": peer})
	return r.status_code, list(r.headers.items()), r.get_data()


def reset(profile):
	'''Puts the app back in its starting state, configured as deployment `profile` (see config.PROFILES; None for the default one).'''
	variables = config.PROFILES[profile] if profile else {}
	if unknown := set(variables) - set(_PROFILE_SETTERS):
		raise KeyError(f"no setter for profile variables {unknown}")
	for name, setter in _PROFILE_SETTERS.items():
		setter(variables.get(name))
	# Release the app's thread-local session so an open transaction can't block the truncate
	db_session.remove()
	background.discard()
	limiter.clock = time.time
	_reset.reset()
	_outbound_attempts.clear()
	_sent_mail.clear()
	_external_responses.clear()
	_external_requests.clear()
	# Installed for the rest of the process; the legacy tests that would mind run before any spec test
	requests.adapters.HTTPAdapter.send = _fake_http_send
	smtplib.SMTP = _CapturingSMTP
	smtplib.SMTP_SSL = _CapturingSMTP


_LIMITS_AT_START = limiter.enabled


def _set_limits(value):
	limiter.enabled = bool_from_string(value) if value is not None else _LIMITS_AT_START


# How each variable a profile may set reaches the app, which read its environment when it started: given the profile's value, or None to put back what the app started with
_PROFILE_SETTERS = {
	"SPEC_TEST_LIMITS": _set_limits,
}


def run_background_work():
	background.drain()


def limit_clock_set(at):
	if at.tzinfo is None:
		raise ValueError(f"the time {at} has no UTC offset")
	timestamp = at.timestamp()
	limiter.clock = lambda: timestamp


def cli(args):
	'''Returns (exit code, what the command printed on stdout).'''
	with background.separately():
		result = app.test_cli_runner().invoke(args=list(args))
	# A command may leave the thread's session holding a transaction; release it like a finished request would
	db_session.remove()
	return result.exit_code, result.stdout


def run_scheduler(at):
	with background.separately():
		tasks_run_due(db_session_factory, lambda: at)
	db_session.remove()


def sent_mail() -> list[dict]:
	return list(_sent_mail)


def take_outbound_attempts():
	attempts = list(_outbound_attempts)
	_outbound_attempts.clear()
	return attempts


def take_server_log() -> str:
	'''What the implementation logged since the test began; an in-process one logs into the test's own output.'''
	return ""


def external_serve(method, url, status, headers, body, trusted):
	_external_responses[external_key(method, url)] = (status, headers, body, trusted)


def external_unreachable(method, url):
	_external_responses[external_key(method, url)] = _UNREACHABLE


def external_requests() -> list[tuple[str, str, bytes]]:
	return [(r["method"], r["url"], r["body"]) for r in _external_requests]


def _body_bytes(body) -> bytes:
	if body is None:
		return b""
	if isinstance(body, str):
		return body.encode()
	if isinstance(body, bytes):
		return body
	raise TypeError(f"an outbound request's body of type {type(body).__name__} can't be recorded")


def _fake_http_send(self, request, *args, **kwargs):
	response = _external_responses.get(external_key(request.method, request.url))
	if response is None:
		_outbound_attempts.append(f"HTTP {request.method} {request.url}")
		raise requests.exceptions.ConnectionError(f"Outbound HTTP is blocked in spec tests: {request.method} {request.url}")
	if response is not _UNREACHABLE and not response[3] and kwargs.get("verify", True) is not False:
		raise requests.exceptions.SSLError(f"{request.url}'s certificate isn't signed by a trusted authority (spec test)")
	_external_requests.append({"method": request.method, "url": request.url, "body": _body_bytes(request.body)})
	if response is _UNREACHABLE:
		raise requests.exceptions.ConnectionError(f"{request.url} is unreachable (spec test)")
	status, headers, body, _trusted = response
	raw = urllib3.HTTPResponse(body=BytesIO(body), headers=headers, status=status, preload_content=False, decode_content=False)
	return self.build_response(request, raw)


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
