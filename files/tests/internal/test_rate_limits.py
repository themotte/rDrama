'''The site's rate limiter (files/helpers/rate_limits.py), beyond what spec/limits says of it through HTTP.'''
import pytest

from files.__main__ import app
from files.helpers.rate_limits import client_address


@pytest.mark.parametrize(("headers", "peer", "address"), [
	({"X-Real-IP": "192.0.2.1"}, "127.0.0.1", "192.0.2.1"),
	({"X-Real-IP": " 192.0.2.1 "}, "127.0.0.1", "192.0.2.1"),
	({}, "198.51.100.7", "198.51.100.7"),
	({"X-Real-IP": ""}, "198.51.100.7", "198.51.100.7"),
	({"X-Real-IP": "  "}, "198.51.100.7", "198.51.100.7"),
], ids=["header", "header with spaces", "peer", "blank header", "spaces only"])
def test_the_client_is_the_real_ip_header_or_else_the_peer(headers, peer, address):
	with app.test_request_context(headers=headers, environ_base={"REMOTE_ADDR": peer}):
		assert client_address() == address
