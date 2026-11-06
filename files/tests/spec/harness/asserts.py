from urllib.parse import parse_qs, urlsplit

from files.tests.spec.harness.http import Client, Response

__all__ = ["assert_status", "assert_redirect", "assert_login_redirect", "assert_api_unauthorized", "assert_json_message", "assert_html", "assert_serves_image", "assert_in_payload", "assert_not_in_payload", "assert_in_order"]


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


def assert_json_message(r: Response):
	'''The standard success reply to a script action: 200 with a JSON object holding just a human-readable "message".'''
	assert_status(r, 200)
	assert r.header("Content-Type").startswith("application/json"), f"expected JSON, got {r.header('Content-Type')}"
	assert set(r.json) == {"message"} and isinstance(r.json["message"], str), r.json


def assert_html(r: Response, status: int):
	'''A rendered page (as opposed to JSON or a redirect).'''
	assert_status(r, status)
	assert r.header("Content-Type").startswith("text/html"), f"expected an HTML page, got {r.header('Content-Type')}"


_IMAGE_SIGNATURES = {
	"image/webp": lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP",
	"image/png": lambda b: b[:8] == b"\x89PNG\r\n\x1a\n",
	"image/gif": lambda b: b[:6] in (b"GIF87a", b"GIF89a"),
	"image/jpeg": lambda b: b[:3] == b"\xff\xd8\xff",
}


def assert_serves_image(url: str):
	'''`url` is publicly fetchable as an image whose bytes match its declared type.'''
	r = Client().get(url)
	assert_status(r, 200)
	content_type = r.header("Content-Type").split(";")[0]
	assert content_type in _IMAGE_SIGNATURES, f"{url} served {content_type}"
	assert _IMAGE_SIGNATURES[content_type](r.body), f"{url} is declared {content_type} but its bytes start {r.body[:12]!r}"


def assert_in_payload(r: Response, token: str):
	'''`token` is somewhere in the response. This says nothing about visual visibility, only that the data was sent.'''
	assert token in r.text, f"expected {token!r} in the response; {_describe(r)}"


def assert_not_in_payload(r: Response, token: str):
	assert token not in r.text, f"expected {token!r} to be absent from the response, but it was sent"


def assert_in_order(r: Response, tokens: list[str]):
	'''Every one of `tokens` is in the response, and they first appear in this order.'''
	for token in tokens:
		assert_in_payload(r, token)
	positions = [r.text.index(token) for token in tokens]
	assert positions == sorted(positions), f"expected {tokens!r} in this order, but they appear in the order {sorted(tokens, key=r.text.index)!r}"
