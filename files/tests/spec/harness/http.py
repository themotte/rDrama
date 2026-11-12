import json as _json
from dataclasses import dataclass
from http.cookies import SimpleCookie
from urllib.parse import quote, urlencode, urlsplit

import urllib3

from files.tests.spec.harness import backend, config, db, run_record, session

DEFAULT_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0"
# The address a client connects from, unless it names another in 127.0.0.0/8
DEFAULT_PEER = "127.0.0.1"


@dataclass
class Response:
	status: int
	headers: list[tuple[str, str]]
	body: bytes

	def header(self, name) -> str | None:
		values = self.header_all(name)
		return values[0] if values else None

	def header_all(self, name) -> list[str]:
		return [v for k, v in self.headers if k.lower() == name.lower()]

	@property
	def text(self) -> str:
		return self.body.decode("utf-8")

	@property
	def json(self):
		return _json.loads(self.body)

	def form_field(self, name) -> str | None:
		'''The value of the first `<input name=...>` in an HTML response. Input names are request-shape contract.'''
		from files.tests.spec.harness.markup import input_value
		return input_value(self, name)

	@property
	def location(self) -> str | None:
		'''The redirect target as a site-relative path (with query), or the absolute URL if it points off-site or if its path would read as one (starting with "//").'''
		loc = self.header("Location")
		if loc is None:
			return None
		parts = urlsplit(loc)
		if parts.netloc and (parts.netloc != config.site_host() or parts.path.startswith("//")):
			return loc
		return parts.path + (f"?{parts.query}" if parts.query else "")


class Client:
	'''A browser-like client: keeps cookies, and when logged in, adds the form key to every non-GET request.'''

	def __init__(self, authorization: str | None = None, peer: str = DEFAULT_PEER):
		self.cookies: dict[str, str] = {}
		self.authorization = authorization
		self.peer = peer

	def login_as(self, user: dict):
		self.cookies[session.cookie_name()] = session.encode(session.logged_in_payload(user["id"], user["login_nonce"]))
		return self

	def session(self) -> dict:
		raw = self.cookies.get(session.cookie_name())
		return session.decode(raw) if raw else {}

	def session_update(self, **values):
		'''Sets keys of the session cookie, as a browser holding such a cookie would send them.'''
		self.cookies[session.cookie_name()] = session.encode({**self.session(), **values})
		return self

	@property
	def user_id(self) -> int | None:
		return self.session().get("lo_user")

	@property
	def formkey(self) -> str | None:
		s = self.session()
		if "lo_user" not in s:
			return None
		users = db.rows("users", id=s["lo_user"])
		if not users:
			return None
		return session.formkey(s["session_id"], s["lo_user"], users[0]["login_nonce"])

	def get(self, path, params=None, headers=None) -> Response:
		return self.request("GET", path, params=params, headers=headers)

	def post(self, path, data=None, headers=None, files=None) -> Response:
		'''`files` maps field name to (filename, bytes, content type), or to a list of them, and makes the request multipart.'''
		return self.request("POST", path, data=self._with_formkey(data), headers=headers, files=files)

	def post_json(self, path, payload, headers=None) -> Response:
		return self.request("POST", path, json=self._with_formkey(payload), headers=headers)

	def post_raw(self, path, data=None, headers=None, files=None) -> Response:
		'''POST without adding the form key, for testing the form-key check itself.'''
		return self.request("POST", path, data=data, headers=headers, files=files)

	def request(self, method, path, *, params=None, data=None, json=None, headers=None, files=None) -> Response:
		if params:
			path = f"{path}{'&' if '?' in path else '?'}{urlencode(params, doseq=True)}"
		all_headers = {"User-Agent": DEFAULT_USER_AGENT, "Host": config.site_host(), **({"Authorization": self.authorization} if self.authorization else {}), **(headers or {})}
		if self.cookies:
			all_headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
		content_type, body = _encode_body(data, json, files)
		if content_type:
			all_headers["Content-Type"] = content_type
		target = request_target(path)
		status, response_headers, body = backend.request(method, target, all_headers, body, self.peer)
		response = Response(status, response_headers, body)
		self._absorb_cookies(response)
		run_record.exchange(method, target, response)
		return response

	def _with_formkey(self, data):
		data = dict(data or {})
		formkey = self.formkey
		if formkey is not None:
			data.setdefault("formkey", formkey)
		return data

	def _absorb_cookies(self, response: Response):
		for header in response.header_all("Set-Cookie"):
			for name, morsel in SimpleCookie(header).items():
				if morsel["max-age"] == "0" or (morsel["expires"] and "1970" in morsel["expires"]):
					self.cookies.pop(name, None)
				else:
					self.cookies[name] = morsel.value


def request_target(path: str) -> str:
	'''The request line's target for `path` (with any query): characters a URL can't hold as written, such as spaces and non-ASCII ones, percent-encoded as UTF-8, and any fragment left off, as browsers send it.'''
	path, has_query, query = path.partition("#")[0].partition("?")
	target = quote(path, safe="%!$&'()*+,/:;=@")
	return target + "?" + quote(query, safe="%!$&'()*+,/:;=?@") if has_query else target


def _fields(data):
	'''(name, value) pairs of a form, a list value giving one pair per item; None values are left out.'''
	for name, value in (data or {}).items():
		for item in value if isinstance(value, list) else [value]:
			if item is not None:
				yield name, str(item)


def _encode_body(data, json, files) -> tuple[str | None, bytes]:
	'''The content type and bytes of a request body: JSON for `json`, multipart when there are `files`, otherwise a URL-encoded form (none when there are no fields).'''
	if json is not None:
		return "application/json", _json.dumps(json).encode()
	if files:
		parts = list(_fields(data))
		for name, value in files.items():
			parts += [(name, f) for f in (value if isinstance(value, list) else [value])]
		body, content_type = urllib3.encode_multipart_formdata(parts)
		return content_type, body
	if not data:
		return None, b""
	return "application/x-www-form-urlencoded", urlencode(list(_fields(data))).encode()
