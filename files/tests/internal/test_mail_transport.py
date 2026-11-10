'''Mail goes to the configured server over STARTTLS that checks the server's certificate and name before the login is sent.'''
import smtplib
import ssl

from flask_mail import Message

from files.__main__ import app, mail


class _RecordingSMTP:
	calls: list = []

	def __init__(self, host="", port=0, *args, **kwargs):
		self.calls.append(("connect", host, port))

	def set_debuglevel(self, level):
		pass

	def starttls(self, *args, context=None, **kwargs):
		self.calls.append(("starttls", context))

	def login(self, user, password, *args, **kwargs):
		self.calls.append(("login", user))

	def sendmail(self, from_addr, to_addrs, msg, *args, **kwargs):
		self.calls.append(("sendmail", list(to_addrs)))
		return {}

	def quit(self):
		pass


def test_starttls_verifies_the_server_before_logging_in(monkeypatch):
	_RecordingSMTP.calls = []
	monkeypatch.setattr(smtplib, "SMTP", _RecordingSMTP)
	monkeypatch.setattr(app.extensions["mail"], "username", "user")
	monkeypatch.setattr(app.extensions["mail"], "password", "secret")

	with app.app_context():
		mail.send(Message(subject="s", body="b", sender="a@example.com", recipients=["b@example.com"]))

	kinds = [call[0] for call in _RecordingSMTP.calls]
	assert kinds == ["connect", "starttls", "login", "sendmail"]
	context = _RecordingSMTP.calls[1][1]
	assert context is not None and context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
