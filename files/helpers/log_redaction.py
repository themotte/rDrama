'''What the logs may record about a request: its URLs and form without passwords, 2FA codes and signed tokens. Everything here is plain string handling on capped input, so it can't raise and costs little whatever a request holds, since it runs on every request, hostile ones included, after the response is built.'''
from itertools import islice
from typing import Mapping
from urllib.parse import quote, unquote, unquote_plus

REDACTED = "[redacted]"

# Longest URL or form value redacted and logged, and most form fields logged; the rest is cut. Cutting before redacting can't expose a secret: a cut name no longer matches, and a matched name's value is replaced whole.
_MAX_LOGGED_LENGTH = 2048
_MAX_LOGGED_FIELDS = 100
_CUT = "…[cut]"

# Form fields and query parameters whose names contain any of these carry passwords, 2FA codes or signed tokens.
_SECRET_NAME_PARTS = ("password", "token", "secret", "formkey", "hash", "captcha", "2fa", "twofactor")

# Parameters carrying a URL on this site that can hold its own tokens: the page to return to after logging in, which a link followed while logged out carries whole.
_URL_PARAMS = ("redirect",)

# Path segments followed by a secret (the 2FA setup QR code embeds the proposed TOTP seed).
_SECRET_PATH_SEGMENTS = ("/2faqr/",)


def _capped(text: str) -> str:
	return text if len(text) <= _MAX_LOGGED_LENGTH else text[:_MAX_LOGGED_LENGTH] + _CUT


def _is_secret(name: str) -> bool:
	name = name.lower()
	return any(part in name for part in _SECRET_NAME_PARTS)


def _redact_path(path: str) -> str:
	decoded = unquote(path)
	for segment in _SECRET_PATH_SEGMENTS:
		at = decoded.find(segment)
		if at >= 0:
			return decoded[:at + len(segment)] + REDACTED
	return path


def _redact_query(query: str, *, nested: bool) -> str:
	segments = []
	for segment in query.split("&"):
		raw_name, eq, value = segment.partition("=")
		name = unquote_plus(raw_name)
		if eq and _is_secret(name):
			value = REDACTED
		elif not nested and name.lower() in _URL_PARAMS:
			carried = unquote_plus(value)
			redacted = redact_url(carried, nested=True)
			if redacted != carried:
				value = quote(redacted, safe="/[]", errors="backslashreplace")
		segments.append(raw_name + eq + value)
	return "&".join(segments)


def redact_request_target(path: str, query: str) -> str:
	'''A request's path and raw query string as the logs record them.'''
	path, query = _capped(path), _capped(query)
	return _redact_path(path) + "?" + _redact_query(query, nested=False)


def redact_url(url: str, *, nested: bool = False) -> str:
	'''`url` (absolute, or a path with an optional query) with secret query values and secret path segments replaced, otherwise exactly as given. A URL carried in a parameter is redacted one level deep.'''
	path, question_mark, query = _capped(url).partition("?")
	return _redact_path(path) + question_mark + (_redact_query(query, nested=nested) if question_mark else "")


def redact_form(form: Mapping[str, str]) -> dict[str, str]:
	'''The form's first fields without its secret ones, values capped, and URLs carried in it redacted.'''
	return {k: redact_url(v, nested=True) if k.lower() in _URL_PARAMS else _capped(v) for k, v in islice(form.items(), _MAX_LOGGED_FIELDS) if not _is_secret(k)}
