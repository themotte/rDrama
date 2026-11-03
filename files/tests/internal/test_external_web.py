'''The spec harness's fake external web, exercised the way the app reaches it: through `requests`.'''
import pytest
import requests

from files.tests.spec.harness import backend, external_web


def test_registered_url_answers_with_its_canned_response():
	external_web.serve("https://example.com/page", status=201, headers={"Content-Type": "text/html"}, body="<p>hi</p>")
	r = requests.get("https://example.com/page?q=1", timeout=5)
	assert (r.status_code, r.headers["Content-Type"], r.text) == (201, "text/html", "<p>hi</p>")
	assert external_web.requests() == [("GET", "https://example.com/page?q=1")]


def test_responses_can_be_streamed():
	external_web.serve("https://example.com/image", body=b"x" * 3000)
	r = requests.get("https://example.com/image", stream=True, timeout=5)
	assert b"".join(r.iter_content(1024)) == b"x" * 3000


def test_matching_ignores_host_case_but_not_method_or_path():
	external_web.serve("https://Example.com/a")
	assert requests.get("https://example.COM/a", timeout=5).status_code == 200
	with pytest.raises(requests.exceptions.ConnectionError):
		requests.post("https://example.com/a", timeout=5)
	with pytest.raises(requests.exceptions.ConnectionError):
		requests.get("https://example.com/b", timeout=5)
	assert backend.take_outbound_attempts() == ["HTTP POST https://example.com/a", "HTTP GET https://example.com/b"]


def test_unreachable_url_fails_like_a_dead_host_without_counting_as_unfaked():
	external_web.unreachable("https://example.com/down")
	with pytest.raises(requests.exceptions.ConnectionError):
		requests.get("https://example.com/down", timeout=5)
	assert external_web.requests() == [("GET", "https://example.com/down")]
	assert backend.take_outbound_attempts() == []


def test_redirects_follow_registered_targets():
	external_web.serve("https://example.com/old", status=302, headers={"Location": "https://example.com/new"})
	external_web.serve("https://example.com/new", body="landed")
	assert requests.get("https://example.com/old", timeout=5).text == "landed"
