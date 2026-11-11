'''
The rest of the internet, as the app sees it. Outbound requests to anything not registered here fail the test; registered URLs answer with canned responses.

URLs match on method, scheme, host and path; the query string is ignored, so a test asserts the query parameters that are contract by inspecting `requests()`. Registrations last until the end of the test.

An out-of-process backend provides this as an intercepting HTTP(S) proxy, so the implementation under test must route its outbound requests through a configured proxy and trust a configured CA bundle.
'''
from files.tests.spec.harness import backend
from files.tests.spec.harness.process_proxy import key


def serve(url: str, *, status: int = 200, headers: dict | None = None, body: bytes | str = b"", method: str = "GET", trusted: bool = True):
	'''Requests to `url` get this response. With `trusted` False, its host (an https one) answers with a certificate no authority the site trusts signed, so a site checking certificates, as it must, gets nothing from it; such requests aren't recorded. A host's certificate is as its latest registration says.'''
	backend.external_serve(method, url, status, headers or {}, body.encode() if isinstance(body, str) else body, trusted)


def unreachable(url: str, *, method: str = "GET"):
	'''Requests to `url` fail as if the host couldn't be reached.'''
	backend.external_unreachable(method, url)


def requests() -> list[tuple[str, str]]:
	'''(method, full url) of every request the app made to a registered URL so far, oldest first.'''
	return [(method, url) for method, url, _body in backend.external_requests()]


def request_bodies(url: str, *, method: str = "GET") -> list[bytes]:
	'''The bodies of the requests the app made so far to registered `url` (matched as registrations are) with `method`, oldest first.'''
	wanted = key(method, url)
	return [body for m, u, body in backend.external_requests() if key(m, u) == wanted]
