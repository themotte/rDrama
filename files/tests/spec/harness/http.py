import json as _json
from dataclasses import dataclass
from html.parser import HTMLParser
from http.cookies import SimpleCookie
from urllib.parse import urlencode, urlsplit

from files.tests.spec.harness import backend, config, db, session

DEFAULT_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0"


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
		parser = _InputFinder(name)
		parser.feed(self.text)
		return parser.value

	@property
	def location(self) -> str | None:
		'''The redirect target as a site-relative path (with query), or the absolute URL if it points off-site.'''
		loc = self.header("Location")
		if loc is None:
			return None
		parts = urlsplit(loc)
		if parts.netloc and parts.netloc != config.site_host():
			return loc
		return parts.path + (f"?{parts.query}" if parts.query else "")


class _InputFinder(HTMLParser):
	def __init__(self, name):
		super().__init__()
		self.name = name
		self.value = None

	def handle_starttag(self, tag, attrs):
		attrs = dict(attrs)
		if tag == "input" and self.value is None and attrs.get("name") == self.name:
			self.value = attrs.get("value", "")


class Client:
	'''A browser-like client: keeps cookies, and when logged in, adds the form key to every non-GET request.'''

	def __init__(self):
		self.cookies: dict[str, str] = {}

	def login_as(self, user: dict):
		self.cookies[session.cookie_name()] = session.encode(session.logged_in_payload(user["id"], user["login_nonce"]))
		return self

	def session(self) -> dict:
		raw = self.cookies.get(session.cookie_name())
		return session.decode(raw) if raw else {}

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

	def post(self, path, data=None, headers=None) -> Response:
		return self.request("POST", path, data=self._with_formkey(data), headers=headers)

	def post_json(self, path, payload, headers=None) -> Response:
		return self.request("POST", path, json=self._with_formkey(payload), headers=headers)

	def post_raw(self, path, data=None, headers=None) -> Response:
		'''POST without adding the form key, for testing the form-key check itself.'''
		return self.request("POST", path, data=data, headers=headers)

	def request(self, method, path, *, params=None, data=None, json=None, headers=None) -> Response:
		if params:
			path = f"{path}{'&' if '?' in path else '?'}{urlencode(params, doseq=True)}"
		all_headers = {"User-Agent": DEFAULT_USER_AGENT, "Host": config.site_host(), **(headers or {})}
		if self.cookies:
			all_headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
		status, response_headers, body = backend.request(method, path, headers=all_headers, data=data, json=json)
		response = Response(status, response_headers, body)
		self._absorb_cookies(response)
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
