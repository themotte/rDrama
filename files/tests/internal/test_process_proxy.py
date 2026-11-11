'''
The intercepting proxy the out-of-process backend gives the site (spec/harness/process_proxy.py), driven as the site drives it: by `requests` in another process, told of the proxy and the session's authority only through its environment.
'''
import json
import os
import socket
import subprocess

import pytest

from files.tests.spec.harness.process_proxy import Proxy
from files.tests.spec.harness.process_tls import Authority

_CLIENT = '''
import json, os, sys
import requests
method, url, data = sys.argv[1], sys.argv[2], sys.argv[3]
try:
	r = requests.request(method, url, data=data or None, timeout=10, verify=bool(os.environ["REQUESTS_CA_BUNDLE"]))
	print(json.dumps({"status": r.status_code, "headers": dict(r.headers), "body": r.text}))
except requests.exceptions.RequestException as e:
	print(json.dumps({"error": type(e).__name__, "connection_error": isinstance(e, requests.exceptions.ConnectionError)}))
'''


@pytest.fixture(scope="module")
def authority(tmp_path_factory):
	return Authority(tmp_path_factory.mktemp("authority"))


@pytest.fixture
def proxy(authority):
	p = Proxy(authority)
	p.start()
	yield p
	p.stop()


def _fetch(proxy, url, *, method="GET", data="", ca_file=None):
	'''`ca_file` "" fetches without checking certificates.'''
	env = {**os.environ, "http_proxy": proxy.url, "https_proxy": proxy.url, "REQUESTS_CA_BUNDLE": proxy.authority.ca_file if ca_file is None else ca_file}
	env.pop("no_proxy", None)
	env.pop("NO_PROXY", None)
	result = subprocess.run(["python3", "-c", _CLIENT, method, url, data], env=env, capture_output=True, text=True, timeout=60)
	assert result.returncode == 0, result.stderr
	return json.loads(result.stdout)


def test_a_registered_https_url_answers_as_registered(proxy):
	proxy.serve("GET", "https://example.com/page", 201, {"Content-Type": "text/plain", "X-Probe": "1"}, b"hello")

	r = _fetch(proxy, "https://example.com/page?q=1")

	assert (r["status"], r["headers"]["X-Probe"], r["body"]) == (201, "1", "hello")
	assert proxy.requests == [{"method": "GET", "url": "https://example.com/page?q=1", "body": b""}]
	assert proxy.take_attempts() == []


def test_a_registered_http_url_answers_too(proxy):
	proxy.serve("POST", "http://example.com/form", 200, {}, b"ok")

	r = _fetch(proxy, "http://example.com/form", method="POST", data="a=1")

	assert r["body"] == "ok"
	assert proxy.requests == [{"method": "POST", "url": "http://example.com/form", "body": b"a=1"}]


def test_a_port_other_than_the_default_is_part_of_the_url(proxy):
	proxy.serve("GET", "https://example.com:8443/", 200, {}, b"ok")

	assert _fetch(proxy, "https://example.com:8443/")["body"] == "ok"
	assert proxy.requests == [{"method": "GET", "url": "https://example.com:8443/", "body": b""}]


def test_a_host_nothing_is_registered_for_is_refused_as_an_attempt(proxy):
	assert _fetch(proxy, "https://elsewhere.example/")["connection_error"]
	assert proxy.take_attempts() == ["HTTPS CONNECT elsewhere.example:443"]


def test_an_unregistered_path_fails_to_connect_as_an_attempt(proxy):
	proxy.serve("GET", "https://example.com/page", 200, {}, b"")

	assert _fetch(proxy, "https://example.com/other")["connection_error"]
	assert proxy.take_attempts() == ["HTTP GET https://example.com/other"]
	assert proxy.requests == []


def test_an_unreachable_url_fails_to_connect_and_is_recorded(proxy):
	proxy.unreachable("GET", "https://example.com/down")

	assert _fetch(proxy, "https://example.com/down")["connection_error"]
	assert proxy.requests == [{"method": "GET", "url": "https://example.com/down", "body": b""}]
	assert proxy.take_attempts() == []



def test_a_client_not_trusting_the_authority_fails_the_test(proxy, tmp_path):
	proxy.serve("GET", "https://example.com/page", 200, {}, b"")

	assert _fetch(proxy, "https://example.com/page", ca_file=Authority(tmp_path).ca_file)["error"] == "SSLError"
	[attempt] = proxy.take_attempts()
	assert attempt.startswith("TLS handshake for example.com:443 failed")


def test_an_untrusted_host_is_refused_by_a_checking_client_and_nothing_is_recorded(proxy):
	proxy.serve("GET", "https://example.com/page", 200, {}, b"content", trusted=False)

	assert _fetch(proxy, "https://example.com/page")["error"] == "SSLError"
	assert (proxy.requests, proxy.take_attempts()) == ([], [])


def test_an_untrusted_host_answers_a_client_that_doesnt_check(proxy):
	proxy.serve("GET", "https://example.com/page", 200, {}, b"content", trusted=False)

	assert _fetch(proxy, "https://example.com/page", ca_file="")["body"] == "content"
	assert proxy.requests == [{"method": "GET", "url": "https://example.com/page", "body": b""}]


def test_a_client_hanging_up_mid_body_is_still_answered_for(proxy):
	proxy.serve("POST", "http://example.com/upload", 200, {}, b"ok")
	host, port = proxy.url.removeprefix("http://").split(":")

	with socket.create_connection((host, int(port))) as s:
		s.sendall(b"POST http://example.com/upload HTTP/1.1\r\nHost: example.com\r\nContent-Length: 100\r\n\r\nshort")
		s.shutdown(socket.SHUT_WR)
		s.recv(1024)

	assert proxy.requests == [{"method": "POST", "url": "http://example.com/upload", "body": b"short"}]
	assert proxy.take_attempts() == []


def test_a_chunked_body_is_recorded_joined(proxy):
	proxy.serve("POST", "http://example.com/form", 200, {}, b"ok")
	host, port = proxy.url.removeprefix("http://").split(":")

	with socket.create_connection((host, int(port))) as s:
		s.sendall(b"POST http://example.com/form HTTP/1.1\r\nHost: example.com\r\nTransfer-Encoding: chunked\r\n\r\n3;x=y\r\na=1\r\n4\r\n&b=2\r\n0\r\nX-Trailer: t\r\n\r\n")
		assert s.recv(1024).startswith(b"HTTP/1.1 200")

	assert proxy.requests == [{"method": "POST", "url": "http://example.com/form", "body": b"a=1&b=2"}]
	assert proxy.take_attempts() == []
