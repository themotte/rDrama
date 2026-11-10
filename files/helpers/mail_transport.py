'''flask_mail, with a STARTTLS that checks the mail server's certificate and name before the login is sent; flask_mail's own checks neither.'''
import smtplib
import ssl

import flask
import flask_mail


class _Connection(flask_mail.Connection):
	def configure_host(self):
		host = smtplib.SMTP(self.mail.server, self.mail.port)
		host.set_debuglevel(int(self.mail.debug))
		host.starttls(context=ssl.create_default_context())
		if self.mail.username and self.mail.password:
			host.login(self.mail.username, self.mail.password)
		return host


class Mail(flask_mail.Mail):
	def connect(self):
		return _Connection((getattr(self, "app", None) or flask.current_app).extensions["mail"])
