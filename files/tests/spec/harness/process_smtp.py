'''
The mail server for an implementation running in its own process (MAIL_SERVER=127.0.0.1, MAIL_PORT): it takes every message over SMTP with STARTTLS, presenting a certificate for that address from the session's authority (process_tls), accepts any login, and records each message as the in-process fake does instead of delivering it. Anything that goes wrong in a conversation is recorded as an attempt, so the test fails.
'''
import base64
import email
import socketserver
import threading
import traceback

_TIMEOUT = 30
# SMTP's own limit is 1000 bytes with the line ending; this only guards against unbounded reads
_LINE_LIMIT = 65536
HOST = "127.0.0.1"


class Capture:
	def __init__(self, authority):
		self.authority = authority
		self.messages: list[dict] = []
		self.attempts: list[str] = []
		self._lock = threading.Lock()
		# Connections still being handled; their outcome isn't recorded yet
		self._open = threading.Condition()
		self._open_count = 0
		capture = self

		class Handler(socketserver.StreamRequestHandler):
			def handle(self):
				with capture._open:
					capture._open_count += 1
				try:
					capture._handle(self.connection)
				finally:
					with capture._open:
						capture._open_count -= 1
						capture._open.notify_all()

		self._server = socketserver.ThreadingTCPServer((HOST, 0), Handler)
		self._server.daemon_threads = True
		self.port = self._server.server_address[1]

	def start(self):
		self.authority.server_context(HOST)
		threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()

	def stop(self):
		self._server.shutdown()
		self._server.server_close()

	def clear(self):
		with self._lock:
			self.messages.clear()
			self.attempts.clear()

	def take_attempts(self) -> list[str]:
		with self._open:
			if not self._open.wait_for(lambda: self._open_count == 0, timeout=_TIMEOUT):
				self._attempt(f"a conversation with the mail capture was still open after {_TIMEOUT} seconds")
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
			_Conversation(self, connection).run()
		except Exception:
			self._attempt(f"the mail capture failed: {traceback.format_exc()}")

	def _record(self, sender, recipients, data):
		with self._lock:
			self.messages.append({"from": sender, "to": recipients, "message": email.message_from_bytes(data)})


class _Conversation:
	def __init__(self, capture, connection):
		self.capture = capture
		self.connection = connection
		self.stream = connection.makefile("rb")
		self.secure = False
		self._reset()

	def _reset(self):
		self.sender, self.recipients = None, []

	def _send(self, line):
		self.connection.sendall(line.encode() + b"\r\n")

	def _line(self) -> str:
		line = self.stream.readline(_LINE_LIMIT + 1)
		if not line:
			raise ConnectionError("the client hung up mid-conversation")
		if len(line) > _LINE_LIMIT:
			raise ValueError(f"a line longer than {_LINE_LIMIT} bytes")
		# latin-1 keeps a message's bytes as they came
		return line.decode("latin-1").rstrip("\r\n")

	def run(self):
		self._send(f"220 {HOST} spec mail capture")
		while True:
			command = self._line()
			verb, _, argument = command.partition(" ")
			verb = verb.upper()
			if verb in ("EHLO", "HELO"):
				features = ["AUTH PLAIN LOGIN"] if self.secure else ["STARTTLS"]
				self._send(f"250-{HOST}" if verb == "EHLO" else f"250 {HOST}")
				if verb == "EHLO":
					for i, feature in enumerate(features):
						self._send(("250 " if i == len(features) - 1 else "250-") + feature)
			elif verb == "STARTTLS" and not self.secure:
				self._send("220 ready")
				self.connection = self.capture.authority.server_context(HOST).wrap_socket(self.connection, server_side=True)
				self.stream = self.connection.makefile("rb")
				self.secure = True
				self._reset()
			elif verb == "AUTH" and self.secure:
				self._authenticate(argument)
			elif verb == "MAIL" and self.secure:
				self.sender = _address(argument)
				self._send("250 ok")
			elif verb == "RCPT" and self.sender is not None:
				self.recipients.append(_address(argument))
				self._send("250 ok")
			elif verb == "DATA" and self.recipients:
				self._send("354 go ahead")
				self.capture._record(self.sender, self.recipients, self._data())
				self._reset()
				self._send("250 ok")
			elif verb == "RSET":
				self._reset()
				self._send("250 ok")
			elif verb == "NOOP":
				self._send("250 ok")
			elif verb == "QUIT":
				self._send("221 bye")
				return
			else:
				raise ValueError(f"unexpected SMTP command {command!r} (secure: {self.secure})")

	def _authenticate(self, argument):
		mechanism, _, initial = argument.partition(" ")
		mechanism = mechanism.upper()
		if mechanism == "PLAIN":
			if not initial:
				self._send("334 ")
				self._line()
		elif mechanism == "LOGIN":
			# The username may come with the command
			for prompt in ("Username:", "Password:")[1 if initial else 0:]:
				self._send(f"334 {base64.b64encode(prompt.encode()).decode()}")
				self._line()
		else:
			raise ValueError(f"unexpected SMTP AUTH mechanism {mechanism!r}")
		self._send("235 accepted")

	def _data(self) -> bytes:
		lines = []
		while (line := self._line()) != ".":
			lines.append(line[1:] if line.startswith(".") else line)
		return "\n".join(lines).encode("latin-1") + b"\n"


def _address(argument):
	'''The address of a MAIL FROM:<...> or RCPT TO:<...> argument, without its parameters.'''
	value = argument.partition(":")[2].strip()
	return value.split(">", 1)[0].lstrip("<") if value.startswith("<") else value.split(" ", 1)[0]
