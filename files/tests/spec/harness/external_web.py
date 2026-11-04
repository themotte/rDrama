'''
The rest of the internet, as the app sees it. Outbound requests to anything not registered here fail the test; registered URLs answer with canned responses.

URLs match on method, scheme, host and path; the query string is ignored, so a test asserts the query parameters that are contract by inspecting `requests()`. Registrations last until the end of the test.

An out-of-process backend provides this as an intercepting HTTP(S) proxy, so the implementation under test must route its outbound requests through a configured proxy and trust a configured CA bundle.
'''
from files.tests.spec.harness import backend


def serve(url: str, *, status: int = 200, headers: dict | None = None, body: bytes | str = b"", method: str = "GET"):
	backend.external_serve(method, url, status, headers or {}, body.encode() if isinstance(body, str) else body)


def unreachable(url: str, *, method: str = "GET"):
	'''Requests to `url` fail as if the host couldn't be reached.'''
	backend.external_unreachable(method, url)


def requests() -> list[tuple[str, str]]:
	'''(method, full url) of every request the app made to a registered URL so far, oldest first.'''
	return backend.external_requests()


def request_details() -> list[dict]:
	'''Like `requests()`, with each request's "method", "url", "headers" and "body" (bytes).'''
	return backend.external_request_details()
