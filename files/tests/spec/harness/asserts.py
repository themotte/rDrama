from urllib.parse import parse_qs, urlsplit

from files.tests.spec.harness.http import Response

__all__ = ["assert_status", "assert_redirect", "assert_login_redirect", "assert_api_unauthorized", "assert_in_payload", "assert_not_in_payload"]


def _describe(r: Response) -> str:
	body = r.body[:500].decode("utf-8", errors="replace")
	return f"status {r.status}, Location {r.header('Location')!r}, body starts {body!r}"


def assert_status(r: Response, status: int):
	assert r.status == status, f"expected status {status}; got {_describe(r)}"


def assert_redirect(r: Response, path: str, query_keys=()):
	'''A 302 to `path` (the status matters: 307/308 would make browsers repeat a POST). Query values are often user-facing copy, so only the presence of `query_keys` is checked.'''
	assert r.status == 302, f"expected a 302 redirect to {path}; got {_describe(r)}"
	parts = urlsplit(r.location)
	assert parts.path == path, f"expected a redirect to {path}; got {r.location}"
	missing = set(query_keys) - set(parse_qs(parts.query))
	assert not missing, f"redirect {r.location} lacks query keys {missing}"


def assert_login_redirect(r: Response, returning_to: str):
	'''A browser sent to log in, to come back to `returning_to` (path plus any query) afterwards.'''
	assert_redirect(r, "/login", query_keys=["redirect"])
	back = parse_qs(urlsplit(r.location).query)["redirect"][0]
	assert back.rstrip("?") == returning_to, f"login redirect returns to {back!r}, expected {returning_to!r}"


def assert_api_unauthorized(r: Response):
	'''API and xhr clients get a JSON error instead of a login redirect.'''
	assert_status(r, 401)
	assert r.json["code"] == 401, r.json


def assert_in_payload(r: Response, token: str):
	'''`token` is somewhere in the response. This says nothing about visual visibility, only that the data was sent.'''
	assert token in r.text, f"expected {token!r} in the response; {_describe(r)}"


def assert_not_in_payload(r: Response, token: str):
	assert token not in r.text, f"expected {token!r} to be absent from the response, but it was sent"
