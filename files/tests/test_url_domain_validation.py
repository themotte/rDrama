"""Tests for URL domain validation — handles & and ? in domain names (#197).

URLs with special characters like & and ? in the domain portion are technically
invalid. Rather than letting them through and causing breakage in title display,
URL rendering, and the is_repost endpoint, we validate the domain and reject
URLs that contain characters not valid in a hostname.
"""

import pytest
from files.helpers.content import canonicalize_url2, has_valid_domain


class TestHasValidDomain:
	"""Test the domain validation helper."""

	def test_valid_simple_domain(self):
		assert has_valid_domain("http://example.com/path") is True

	def test_valid_subdomain(self):
		assert has_valid_domain("https://www.example.com/path") is True

	def test_valid_domain_with_port(self):
		assert has_valid_domain("http://example.com:8080/path") is True

	def test_valid_ip_address(self):
		assert has_valid_domain("http://192.168.1.1/path") is True

	def test_valid_ipv6(self):
		assert has_valid_domain("http://[::1]/path") is True

	def test_valid_idn_domain(self):
		assert has_valid_domain("http://xn--nxasmq6b.com/path") is True

	def test_valid_domain_with_hyphen(self):
		assert has_valid_domain("http://my-site.example.com/path") is True

	def test_invalid_ampersand_in_domain(self):
		"""The core bug from issue #197: & in domain."""
		assert has_valid_domain("http://aba&bbb?ccc.com/def1.txt") is False

	def test_invalid_question_mark_parsed_as_query(self):
		"""When ? appears after a valid domain, it's a query string separator, not domain."""
		# This URL has a valid domain (example.com) with a query string
		assert has_valid_domain("http://example.com?query=1") is True

	def test_invalid_ampersand_only_in_domain(self):
		assert has_valid_domain("http://foo&bar.com/path") is False

	def test_invalid_exclamation_in_domain(self):
		assert has_valid_domain("http://foo!bar.com/path") is False

	def test_invalid_space_in_domain(self):
		assert has_valid_domain("http://foo bar.com/path") is False

	def test_invalid_hash_in_domain(self):
		"""# in a URL is a fragment separator, not part of the domain."""
		# urlparse treats # as fragment separator so netloc won't contain it
		# This test verifies normal behavior
		assert has_valid_domain("http://example.com#fragment") is True

	def test_empty_url(self):
		assert has_valid_domain("") is False

	def test_no_scheme(self):
		"""URL without scheme — urlparse puts everything in path, empty netloc."""
		assert has_valid_domain("example.com/path") is False

	def test_valid_url_with_query_and_fragment(self):
		assert has_valid_domain("https://example.com/path?q=1&r=2#frag") is True

	def test_valid_url_with_userinfo(self):
		"""URLs with user:pass@host are unusual but have valid netloc structure."""
		assert has_valid_domain("http://user:pass@example.com/path") is True


class TestCanonicalizeUrl2WithInvalidDomains:
	"""Test that canonicalize_url2 returns None for invalid domains."""

	def test_ampersand_in_domain_returns_none(self):
		result = canonicalize_url2("http://aba&bbb?ccc.com/def1.txt", httpsify=True)
		assert result is None

	def test_ampersand_in_domain_without_httpsify_returns_none(self):
		result = canonicalize_url2("http://foo&bar.com/path", httpsify=False)
		assert result is None

	def test_valid_url_still_works(self):
		result = canonicalize_url2("http://example.com/path?utm_source=test", httpsify=True)
		assert result is not None
		assert result.netloc == "example.com"
		assert result.scheme == "https"

	def test_valid_url_with_ampersand_in_query(self):
		"""& in query string is normal and should not be rejected."""
		result = canonicalize_url2("http://example.com/path?a=1&b=2", httpsify=True)
		assert result is not None
		assert result.netloc == "example.com"

	def test_valid_url_without_httpsify(self):
		result = canonicalize_url2("http://example.com/path", httpsify=False)
		assert result is not None
		assert result.scheme == "http"


class TestIsRepostWithInvalidUrls:
	"""Integration tests for is_repost endpoint with malformed URLs."""

	def test_is_repost_with_ampersand_in_domain(self):
		"""is_repost should return empty permalink for invalid domain URLs."""
		from . import util, util_accounts
		client, user = util_accounts.create_test_client_and_user()

		response, _ = util.post_with_formkey(
			client, "/is_repost",
			data={"url": "http://aba&bbb?ccc.com/def1.txt"}
		)
		# Should not crash — should return 200 with empty permalink or 400
		assert response.status_code in [200, 400]
		if response.status_code == 200:
			import json
			data = json.loads(response.data)
			assert data.get("permalink") == ""

	def test_is_repost_with_question_mark_in_domain(self):
		"""is_repost should handle ? in domain gracefully."""
		from . import util, util_accounts
		client, user = util_accounts.create_test_client_and_user()

		response, _ = util.post_with_formkey(
			client, "/is_repost",
			data={"url": "http://foo?bar.com/path"}
		)
		assert response.status_code in [200, 400]
		if response.status_code == 200:
			import json
			data = json.loads(response.data)
			assert data.get("permalink") == ""

	def test_is_repost_valid_url_still_works(self):
		"""Normal URLs should still work in is_repost."""
		from . import util, util_accounts
		client, user = util_accounts.create_test_client_and_user()

		response, _ = util.post_with_formkey(
			client, "/is_repost",
			data={"url": "https://example.com/test-page"}
		)
		assert response.status_code == 200
		import json
		data = json.loads(response.data)
		# No repost exists, so permalink should be empty
		assert data.get("permalink") == ""


class TestSubmissionWithInvalidUrls:
	"""Test that submitting a post with an invalid domain URL is handled."""

	def test_submit_with_ampersand_in_domain(self):
		"""Submitting a URL with & in the domain should return an error."""
		from . import util, util_accounts
		client, user = util_accounts.create_test_client_and_user()

		response, _ = util.post_with_formkey(
			client, "/submit",
			data={
				"title": "Test invalid URL",
				"url": "http://aba&bbb?ccc.com/def1.txt",
				"body": "",
			}
		)
		# Should return 400 error, not crash
		assert response.status_code == 400

	def test_submit_with_valid_url_still_works(self):
		"""Normal URL submission should still work."""
		from . import util, util_accounts, util_submissions
		client, user = util_accounts.create_test_client_and_user(name="urltest")

		post = util_submissions.create_submission_for_client(client, data={
			"url": "https://example.com/valid-page",
		})
		assert post is not None
		assert post.url == "https://example.com/valid-page"
