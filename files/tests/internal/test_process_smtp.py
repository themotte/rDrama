'''
The mail capture the out-of-process backend gives the site (spec/harness/process_smtp.py), driven by smtplib in another process over STARTTLS that checks the capture's certificate, as the site sends mail.
'''
import subprocess

import pytest

from files.tests.spec.harness.process_smtp import HOST, Capture
from files.tests.spec.harness.process_tls import Authority

_CLIENT = '''
import smtplib, ssl, sys
port, ca_file, mechanism = int(sys.argv[1]), sys.argv[2], sys.argv[3]
message = b"Subject: probe\\r\\nTo: b@example.com\\r\\n\\r\\nfirst line\\r\\n.leading dot\\r\\n..two dots\\r\\n"
host = smtplib.SMTP(sys.argv[4], port, timeout=10)
try:
	host.starttls(context=ssl.create_default_context(cafile=ca_file))
except ssl.SSLError as e:
	print("SSLError")
	sys.exit(0)
host.user, host.password = "user", "secret"
host.auth(mechanism, getattr(host, "auth_" + mechanism.lower()))
host.sendmail("a@example.com", ["b@example.com", "c@example.com"], message)
host.quit()
print("sent")
'''


@pytest.fixture(scope="module")
def authority(tmp_path_factory):
	return Authority(tmp_path_factory.mktemp("authority"))


@pytest.fixture
def capture(authority):
	c = Capture(authority)
	c.start()
	yield c
	c.stop()


def _send(capture, *, mechanism="PLAIN", ca_file=None):
	result = subprocess.run(["python3", "-c", _CLIENT, str(capture.port), ca_file or capture.authority.ca_file, mechanism, HOST], capture_output=True, text=True, timeout=60)
	assert result.returncode == 0, result.stderr
	return result.stdout.strip()


@pytest.mark.parametrize("mechanism", ["PLAIN", "LOGIN"])
def test_a_message_is_recorded_as_sent(capture, mechanism):
	assert _send(capture, mechanism=mechanism) == "sent"

	[mail] = capture.messages
	assert (mail["from"], mail["to"], mail["message"]["Subject"]) == ("a@example.com", ["b@example.com", "c@example.com"], "probe")
	assert mail["message"].get_payload() == "first line\n.leading dot\n..two dots\n"
	assert capture.take_attempts() == []


def test_a_client_not_trusting_the_authority_fails_the_test(capture, tmp_path):
	assert _send(capture, ca_file=Authority(tmp_path).ca_file) == "SSLError"

	assert capture.messages == []
	[attempt] = capture.take_attempts()
	assert "SSL" in attempt
