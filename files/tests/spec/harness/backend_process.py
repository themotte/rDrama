'''
Out-of-process backend: drives an implementation running in its own processes, started by the commands its runner names, and stands in for the world around it: an intercepting proxy for the outbound web (process_proxy) and a mail server (process_smtp), whose certificates come from a session authority (process_tls).

The test-mode interface an implementation provides to be run by the spec:
- The site. RDRAMA_SPEC_SERVER is a command that serves the site over HTTP/1.1 on 127.0.0.1, at the port its "{port}" stands for. It runs with the harness's environment (which sets SPEC_TEST_MODE, see config.Env.TEST) and, added to it:
  - http_proxy, https_proxy, HTTP_PROXY and HTTPS_PROXY naming the proxy, and no no_proxy. The site sends all its outbound HTTP through it: plain HTTP as absolute-form requests, HTTPS through CONNECT tunnels. The proxy reads each request's body, by its Content-Length or chunked, and answers it with Connection: close; it refuses a CONNECT to a host nothing is registered for with 502, and hangs up on a request for a URL nothing is registered for, or registered as unreachable.
  - SSL_CERT_FILE naming the authority's certificate, which the site trusts, in place of any other, for its outbound HTTPS and its mail server.
  - MAIL_SERVER (an IP address) and MAIL_PORT naming the mail capture, which the site reaches over STARTTLS.
  It takes connections from any address in 127.0.0.0/8, and takes the address a connection comes from for the request's peer (harness.Client's `peer`). It serves from one process, since the background work it holds is that process's, and closes a connection after the response when the request asks it to (Connection: close). Requests come one at a time; each must be answered within 30 seconds. A response may come before the site has read the request's body (refusing a body by its length), and the connection may then be reset once it is sent.
- Shared state. The database, the Redis db, the site settings file and the upload store are the state the environment configures. The harness reads and writes them directly, between requests and between tests (state.py puts them back before each test), so the site keeps no copy of them across requests that such a change would leave stale, and holds no transaction open between requests, which would hold up the reset's truncate.
- Control requests, answered in test mode only, whatever their Host, ahead of any of the site's own handling:
  - POST /__spec__/ready answers once the site serves requests; the harness retries it while the connection is refused, for up to 60 seconds, and takes any other answer than 200 for a failure to start.
  - POST /__spec__/background/run runs the work the site has handed to the background to completion.
  - POST /__spec__/reset drops that work unrun, and sets the clock below back to the real time.
  - POST /__spec__/clock, with the JSON body {"at": <a time in ISO 8601 with its UTC offset, perhaps with fractions of a second>}, stops the clock the rate limits and the signup form's minimum filling time are measured by at that time, until it is set again or reset (harness.limit_clock_set).
  Each answers 200 with a JSON object whose "boot" names the process serving (the same for its whole life) if what it asked for ran without error, and otherwise 500 with a description of the error, such as a traceback, as the body.
- Commands. RDRAMA_SPEC_CLI is a command prefix: followed by a command's name and arguments, it runs that command (harness.cli) with the site's environment, doing the work it hands to the background before it exits. Its exit status and stdout are the result; its stderr is diagnostics. It has 300 seconds.
- The scheduler. RDRAMA_SPEC_SCHEDULER is a command whose "{at}" stands for a time in ISO 8601 with its UTC offset, perhaps with fractions of a second ("2024-01-08T08:00:00+00:00"). It does one pass of the scheduled-task worker on a clock reading that time (harness.run_scheduler), does the work the pass hands to the background, and exits 0 when the pass ran. It has 300 seconds.

- Deployment profiles (config.PROFILES). The harness runs a separate site for each profile its tests use, with the profile's variables added to its environment and to its commands' and scheduler's. Only one site serves at a time, the current test's; the others keep running, idle.

Each site starts with the first test in its profile and stops when the harness's process exits, or dies with it. If it can't start, or stops serving, every test in its profile from then on fails at once with its log.

A run of the whole spec tier also checks the implementation by what its answers show the harness's clients: route coverage (coverage.py), where every route of the table must have answered some test outside spec/routes and spec/limits past its gate, so that the spec, run against this implementation, exercised each; and where pages lead (pages.py), where no link, form or embed of a page may lead to an address no route answers. Neither sees routes the implementation adds beyond the table, nor a missing route it answers with a status other than 404 or 405; pages.py says what of a page it doesn't read.

The runner: what runs the spec tier (pytest, with pytest-xdist for workers) provides around the harness.
- It runs it on Python RUNNER_PYTHON with the packages of RUNNER_PACKAGES, on Linux with the `openssl` command (process_tls), and `setpriv` where it can, so sites die with their harness.
- In each process (each xdist worker), before importing the harness: a database built fresh from the contract's schema.sql and seed.sql (holding nothing else, state.py's snapshot included), on a PostgreSQL role allowed to set session_replication_role (a superuser), for state.py's restore; and the environment of config.SPEC_RUN, config.RUNNER_CHOSEN, config.PRECONDITIONS (or the variables left out) and RDRAMA_SPEC_SERVER, RDRAMA_SPEC_CLI and RDRAMA_SPEC_SCHEDULER.
- It collects the spec tier with its own conftest (spec/conftest.py), whose fixture puts the state and the site back before every test (lifecycle).
- The `profile` mark: registered, a name not in config.PROFILES refused, and under xdist each profile's tests kept to one worker (an xdist_group mark per profile, added before xdist reads the marks, and `--dist loadgroup`).
- Around each spec test's call phase only (not its fixtures): run_record.start(the test's file, check_pages=whether the run checks a whole spec tier) and run_record.stop().
- At the end of a passing run that collected the whole tier (coverage.collected_whole_spec, given the tests collected and the number deselected), from every worker's coverage.seen() and pages.output(): the run fails when coverage.unrequested(all seen) or pages.problems(all outputs) reports anything. A worker that crashed sends nothing, which makes the run incomplete, so these checks don't run.
'''
import atexit
import json
import os
import shlex
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from files.tests.spec.harness import config, state
from files.tests.spec.harness.process_proxy import Proxy
from files.tests.spec.harness.process_smtp import HOST as MAIL_HOST, Capture
from files.tests.spec.harness.process_tls import Authority

__all__ = ["request", "reset", "run_background_work", "limit_clock_set", "cli", "run_scheduler", "sent_mail", "take_outbound_attempts", "take_server_log", "external_serve", "external_unreachable", "external_requests"]

RUNNER_PYTHON = "3.13"
'''The Python version the harness runs on.'''

RUNNER_PACKAGES = {
	"pytest": "8.4.2",
	"pytest-xdist": "3.8.0",
	"SQLAlchemy": "2.0.43",
	"psycopg2": "2.9.10",
	"redis": "6.4.0",
	"lxml": "6.0.2",
	"selectolax": "1.0.2",
	"itsdangerous": "2.2.0",
	"pillow": "11.3.0",
	"pyotp": "2.9.0",
	"urllib3": "2.5.0",
}
'''The Python distributions the harness and the spec's tests run with, at the versions they are known to run with: what they import, the database driver and the runner's.'''

_TIMEOUT = 30
_START_TIMEOUT = 60
_COMMAND_TIMEOUT = 300
_BODY_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_HARNESS_ADDRESS = "127.0.0.1"


class SiteDown(Exception):
	pass


class _Site:
	def __init__(self, profile):
		self.dir = Path(tempfile.mkdtemp(prefix="spec-site-"))
		self.authority = Authority(self.dir / "authority")
		self.proxy = Proxy(self.authority)
		self.mail = Capture(self.authority)
		self.env = {**os.environ, **(config.PROFILES[profile] if profile else {}), "SSL_CERT_FILE": self.authority.ca_file, "MAIL_SERVER": MAIL_HOST, "MAIL_PORT": str(self.mail.port)}
		for name in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
			self.env[name] = self.proxy.url
		for name in ("no_proxy", "NO_PROXY"):
			self.env.pop(name, None)
		self.log_path = self.dir / "site.log"
		self.log = open(self.log_path, "ab", buffering=0)
		self.log_offset = 0
		self.port = _free_port()
		self.boot = None
		self.process = subprocess.Popen(_with_parent_death(_command("RDRAMA_SPEC_SERVER", port=str(self.port))), env=self.env, stdin=subprocess.DEVNULL, stdout=self.log, stderr=subprocess.STDOUT, start_new_session=True)
		atexit.register(self.stop)
		self.proxy.start()
		self.mail.start()
		try:
			self._wait_until_ready()
		except Exception:
			self.stop()
			raise

	def _wait_until_ready(self):
		deadline = time.monotonic() + _START_TIMEOUT
		while True:
			if self.process.poll() is not None:
				raise SiteDown(f"the site exited with status {self.process.returncode} before serving:\n{self.full_log()}")
			try:
				self.control("ready")
				return
			except RuntimeError as e:
				raise SiteDown(f"the site failed to start: {e}\n{self.full_log()}") from e
			except ConnectionRefusedError:
				if time.monotonic() > deadline:
					raise SiteDown(f"the site didn't answer within {_START_TIMEOUT} seconds:\n{self.full_log()}")
				time.sleep(0.1)

	def control(self, name, payload=None):
		status, _headers, body = self.request("POST", f"/__spec__/{name}", {"Host": config.site_host(), "Content-Type": "application/json"}, json.dumps(payload).encode() if payload is not None else b"", _HARNESS_ADDRESS)
		if status != 200:
			raise RuntimeError(f"the site's /__spec__/{name} answered {status}:\n{body.decode(errors='replace')}")
		boot = json.loads(body)["boot"]
		if self.boot is None:
			self.boot = boot
		elif boot != self.boot:
			raise RuntimeError(f"the site's serving process changed (boot {self.boot} became {boot}), losing what it held:\n{self.take_log()}")

	def request(self, method, target, headers, body, peer):
		try:
			connection = socket.create_connection(("127.0.0.1", self.port), timeout=_TIMEOUT, source_address=(peer, 0))
		except ConnectionRefusedError:
			if self.boot is not None and self.process.poll() is not None:
				raise SiteDown(f"the site exited with status {self.process.returncode}:\n{self.take_log()}")
			raise
		with connection:
			head = [f"{method} {target} HTTP/1.1", *(f"{name}: {value}" for name, value in headers.items())]
			if body or method in _BODY_METHODS:
				head.append(f"Content-Length: {len(body)}")
			head.append("Connection: close")
			connection.sendall(("\r\n".join(head) + "\r\n\r\n").encode("latin-1"))
			# Sent while the response is read: a site may answer before it has read the body (refusing it by its length), and stop reading
			send_errors = []
			sender = threading.Thread(target=_send_body, args=(connection, body, send_errors), daemon=True)
			sender.start()
			received = _read_to_end(connection)
			sender.join(_TIMEOUT)
		if not received:
			raise send_errors[0] if send_errors else ConnectionError(f"the site closed the connection without answering {method} {target}")
		return _parse_response(method, received)

	def run(self, variable, *args, **placeholders) -> subprocess.CompletedProcess:
		result = subprocess.run([*_command(variable, **placeholders), *args], env=self.env, stdin=subprocess.DEVNULL, capture_output=True, timeout=_COMMAND_TIMEOUT)
		self.log.write(result.stderr)
		return result

	def take_log(self) -> str:
		with open(self.log_path, "rb") as f:
			f.seek(self.log_offset)
			text = f.read()
		self.log_offset += len(text)
		return text.decode(errors="replace")

	def full_log(self) -> str:
		return self.log_path.read_text(errors="replace")

	def stop(self):
		if self.process.poll() is None:
			self.process.terminate()
			try:
				self.process.wait(10)
			except subprocess.TimeoutExpired:
				self.process.kill()
		self.proxy.stop()
		self.mail.stop()
		self.log.close()
		shutil.rmtree(self.dir, ignore_errors=True)


# A site per deployment profile (None: the default one), and the one the current test runs against
_sites: dict[str | None, _Site] = {}
_start_failures: dict[str | None, SiteDown] = {}
_profile: str | None = None


def _the_site() -> _Site:
	if _profile in _start_failures:
		raise SiteDown(f"the site couldn't start earlier in this run:\n{_start_failures[_profile]}")
	if _profile not in _sites:
		try:
			_sites[_profile] = _Site(_profile)
		except SiteDown as e:
			_start_failures[_profile] = e
			raise
	return _sites[_profile]


def _command(variable, **placeholders) -> list[str]:
	'''The command a variable names, split as a shell would, with its {placeholders} filled in each word.'''
	words = shlex.split(os.environ[variable])
	for name, value in placeholders.items():
		words = [word.replace("{" + name + "}", value) for word in words]
	return words


def _with_parent_death(command):
	'''
	The command, made to get SIGTERM when the harness's process dies, where the system can arrange it.

	Strictly, the signal comes when the thread that started it ends; tests run on the process's main thread, which starts the site.
	'''
	return ["setpriv", "--pdeathsig", "TERM", "--", *command] if shutil.which("setpriv") else command


def _free_port() -> int:
	with socket.socket() as s:
		s.bind(("127.0.0.1", 0))
		return s.getsockname()[1]


def _send_body(connection, body, errors):
	try:
		connection.sendall(body)
	except OSError as e:
		errors.append(e)


def _read_to_end(connection) -> bytes:
	'''Everything the site sends before it closes the connection. A reset after it has sent something ends it too: a site that answers before reading a whole body may close with the rest unread, and the system then resets the connection.'''
	received = []
	while True:
		try:
			chunk = connection.recv(65536)
		except ConnectionResetError:
			if received:
				break
			raise
		if not chunk:
			break
		received.append(chunk)
	return b"".join(received)


def _parse_response(method, response):
	'''
	(status, [(header, value), ...], body) of a response read to the end of its connection.

	Whatever follows the headers is the body (de-chunked when chunked), so bytes a site sends where none belong, such as after a HEAD's headers, show in it; a body shorter than its Content-Length fails.
	'''
	head, separator, rest = response.partition(b"\r\n\r\n")
	if not separator:
		raise ConnectionError(f"the site's response ended inside its headers: {response[:200]!r}")
	lines = head.decode("latin-1").split("\r\n")
	status = int(lines[0].split(" ", 2)[1])
	headers = [(name, value.strip()) for name, _, value in (line.partition(":") for line in lines[1:])]
	values = {name.lower(): value for name, value in headers}
	if method == "HEAD" or status in (204, 304):
		return status, headers, rest
	if "chunked" in values.get("transfer-encoding", "").lower():
		return status, headers, _dechunk(rest)
	if "content-length" in values and len(rest) < int(values["content-length"]):
		raise ConnectionError(f"the site's response ended {int(values['content-length']) - len(rest)} bytes short of its Content-Length")
	return status, headers, rest


def _dechunk(data):
	body = []
	while True:
		size_line, separator, data = data.partition(b"\r\n")
		if not separator:
			raise ConnectionError("the site's chunked response ended inside a chunk size")
		size = int(size_line.split(b";")[0], 16)
		if size == 0:
			# Trailers, then anything beyond the message
			_trailers, _, extra = data.partition(b"\r\n\r\n") if not data.startswith(b"\r\n") else (b"", b"", data[2:])
			return b"".join(body) + extra
		if len(data) < size + 2:
			raise ConnectionError("the site's chunked response ended inside a chunk")
		body.append(data[:size])
		data = data[size + 2:]


def request(method, target, headers, body, peer):
	'''Sends a request (`target` as on the request line, `body` encoded as `headers` say) from address `peer`. Returns (status, [(header, value), ...], body bytes).'''
	return _the_site().request(method, target, headers, body, peer)


def reset(profile):
	'''Puts the site back in its starting state, and has the test run against the site deployed as `profile` (see config.PROFILES; None for the default one).'''
	global _profile
	# Before the first site starts: the snapshot holds the database as built, and the site finds its settings file
	state.snapshot()
	state.write_site_settings()
	_profile = profile
	site = _the_site()
	site.control("reset")
	state.reset()
	site.proxy.clear()
	site.mail.clear()
	site.take_log()


def run_background_work():
	_the_site().control("background/run")


def limit_clock_set(at):
	_the_site().control("clock", {"at": at.isoformat()})


def cli(args):
	'''Returns (exit code, what the command printed on stdout).'''
	result = _the_site().run("RDRAMA_SPEC_CLI", *args)
	return result.returncode, result.stdout.decode()


def run_scheduler(at):
	result = _the_site().run("RDRAMA_SPEC_SCHEDULER", at=at.isoformat())
	if result.returncode != 0:
		raise RuntimeError(f"the scheduler pass exited with status {result.returncode}:\n{result.stderr.decode(errors='replace')}")


def sent_mail() -> list[dict]:
	return list(_the_site().mail.messages)


def take_outbound_attempts():
	'''Outbound attempts since the test began; none when its site isn't running, since a site that didn't start has already failed the test.'''
	site = _sites.get(_profile)
	if site is None:
		return []
	return site.proxy.take_attempts() + site.mail.take_attempts()


def take_server_log() -> str:
	site = _sites.get(_profile)
	return site.take_log() if site is not None else ""


def external_serve(method, url, status, headers, body, trusted):
	_the_site().proxy.serve(method, url, status, headers, body, trusted)


def external_unreachable(method, url):
	_the_site().proxy.unreachable(method, url)


def external_requests() -> list[tuple[str, str, bytes]]:
	return [(r["method"], r["url"], r["body"]) for r in _the_site().proxy.requests]
