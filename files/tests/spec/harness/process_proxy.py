'''
The rest of the internet for an implementation running in its own process: an HTTP proxy it sends its outbound requests through (http_proxy, https_proxy), answering for the URLs `external_web` registers and refusing everything else. HTTPS requests reach it as CONNECT tunnels, whose TLS it ends with certificates from the session's authority (process_tls), or, for hosts registered as untrusted, from an authority the site isn't told of.

What it records matches the in-process backend: requests to registered URLs, and as outbound attempts, which fail the test, requests to anything else. Whatever else goes wrong here (a failed handshake, a request it can't read) is recorded as an attempt too, so a broken proxy fails the test rather than passing for a site that can't be reached.
'''
import socketserver
import ssl
import threading
import traceback
from http import HTTPStatus
from urllib.parse import urlsplit

from files.tests.spec.harness.process_tls import Authority

_DEFAULT_PORTS = {"http": 80, "https": 443}
_TIMEOUT = 30


class Unreachable:
	pass


UNREACHABLE = Unreachable()


def key(method: str, url: str) -> tuple:
	'''What a registration matches on: method, scheme, host (with any port) and path; the query is ignored.'''
	parts = urlsplit(url)
	return (method.upper(), parts.scheme.lower(), parts.netloc.lower(), parts.path or "/")


class Proxy:
	def __init__(self, authority):
		self.authority = authority
		self.responses: dict[tuple, object] = {}
		# Hosts whose certificate comes from an authority the site doesn't trust
		self.untrusted: set[str] = set()
		self._stranger: Authority | None = None
		self.requests: list[dict] = []
		self.attempts: list[str] = []
		self._lock = threading.Lock()
		# Connections still being handled; their outcome isn't recorded yet
		self._open = threading.Condition()
		self._open_count = 0
		proxy = self

		class Handler(socketserver.StreamRequestHandler):
			def handle(self):
				with proxy._open:
					proxy._open_count += 1
				try:
					proxy._handle(self.connection)
				finally:
					with proxy._open:
						proxy._open_count -= 1
						proxy._open.notify_all()

		self._server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler, bind_and_activate=True)
		self._server.daemon_threads = True
		self.url = f"http://127.0.0.1:{self._server.server_address[1]}"

	def start(self):
		threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()

	def stop(self):
		self._server.shutdown()
		self._server.server_close()

	def serve(self, method, url, status, headers, body, trusted=True):
		self._register(method, url, (status, headers, body), trusted)

	def unreachable(self, method, url):
		self._register(method, url, UNREACHABLE, True)

	def _register(self, method, url, response, trusted):
		parts = urlsplit(url)
		if parts.scheme == "https":
			(self.untrusted.discard if trusted else self.untrusted.add)(parts.hostname)
			# Made here, so a failure shows in the test that registered the URL
			self._context(parts.hostname)
		self.responses[key(method, url)] = response

	def _context(self, host):
		if host not in self.untrusted:
			return self.authority.server_context(host)
		if self._stranger is None:
			self._stranger = Authority(self.authority.dir / "stranger")
		return self._stranger.server_context(host)

	def clear(self):
		with self._lock:
			self.responses.clear()
			self.untrusted.clear()
			self.requests.clear()
			self.attempts.clear()

	def take_attempts(self) -> list[str]:
		with self._open:
			if not self._open.wait_for(lambda: self._open_count == 0, timeout=_TIMEOUT):
				self._attempt(f"a connection to the proxy was still open after {_TIMEOUT} seconds")
		with self._lock:
			attempts = list(self.attempts)
			self.attempts.clear()
		return attempts

	def _attempt(self, description):
		with self._lock:
			self.attempts.append(description)

	def _handle(self, connection):
		connection.settimeout(_TIMEOUT)
		try:
			stream = connection.makefile("rb")
			method, target, headers = _read_head(stream)
			if method == "CONNECT":
				self._tunnel(connection, target)
			else:
				self._answer(connection, stream, method, target, headers)
		except _ClientGone:
			# Connected and left without asking for anything
			pass
		except Exception:
			self._attempt(f"the proxy failed: {traceback.format_exc()}")

	def _tunnel(self, connection, authority):
		host, _, port = authority.rpartition(":")
		netloc = host.lower() if int(port) == _DEFAULT_PORTS["https"] else f"{host.lower()}:{port}"
		if not any(scheme == "https" and registered == netloc for _, scheme, registered, _ in list(self.responses)):
			self._attempt(f"HTTPS CONNECT {authority}")
			connection.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
			return
		connection.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
		try:
			tls = self._context(host).wrap_socket(connection, server_side=True)
		except (ssl.SSLError, OSError) as e:
			# Refusing an untrusted certificate is what a site does; anything else is a failure here
			if host not in self.untrusted:
				self._attempt(f"TLS handshake for {authority} failed: {e}")
			return
		stream = tls.makefile("rb")
		try:
			method, target, headers = _read_head(stream)
		except _ClientGone:
			self._attempt(f"the site set up a TLS tunnel to {authority} and left without a request")
			return
		self._answer(tls, stream, method, f"https://{netloc}{target}", headers)

	def _answer(self, connection, stream, method, url, headers):
		length = int(headers.get("content-length", "0"))
		try:
			stream.read(length)
		except OSError:
			# A site may hang up mid-body; what it asked for is answered for all the same
			pass
		response = self.responses.get(key(method, url))
		if response is None:
			self._attempt(f"HTTP {method} {url}")
			return
		with self._lock:
			self.requests.append({"method": method, "url": url})
		if response is UNREACHABLE:
			return
		status, response_headers, body = response
		names = {name.lower() for name in response_headers}
		lines = [f"HTTP/1.1 {status} {_reason(status)}", *(f"{name}: {value}" for name, value in response_headers.items())]
		if "content-length" not in names:
			lines.append(f"Content-Length: {len(body)}")
		lines.append("Connection: close")
		try:
			connection.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + body)
		except OSError:
			# The site may stop reading once it has what it wants, as a fetch with a size limit does
			pass


class _ClientGone(Exception):
	pass


def _read_head(stream):
	'''(method, target, {lowercased header name: value}) of the request at the start of `stream`.'''
	request_line = stream.readline(65537)
	if not request_line:
		raise _ClientGone()
	method, target, _version = request_line.decode("latin-1").rstrip("\r\n").split(" ")
	headers = {}
	while (line := stream.readline(65537)) not in (b"\r\n", b"\n", b""):
		name, _, value = line.decode("latin-1").partition(":")
		headers[name.strip().lower()] = value.strip()
	return method, target, headers


def _reason(status):
	try:
		return HTTPStatus(status).phrase
	except ValueError:
		return "Unknown"

