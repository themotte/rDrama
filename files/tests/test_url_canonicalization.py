import pytest
import re
from files.helpers.content import canonicalize_url2
from files.helpers.config.regex import utm_regex, utm_regex2


def test_url_canonicalization_with_utm_parameters():
	"""Test URL canonicalization with UTM and tracking parameter removal."""

	test_cases = [
		# (input_url, expected_output)
		(
			"https://freddiedeboer.substack.com/p/my-response-to-daniel-bergners-new?utm_source=publication-search",
			"https://freddiedeboer.substack.com/p/my-response-to-daniel-bergners-new"
		),
		(
			"https://example.com/page?utm_source=test",
			"https://example.com/page"
		),
		(
			"https://example.com/page?utm_campaign=test&keep=this",
			"https://example.com/page?keep=this"
		),
		(
			"https://example.com/page?ref_source=test",
			"https://example.com/page"
		),
		(
			"https://example.com/page?normal=param&utm_medium=test",
			"https://example.com/page?normal=param"
		),
		(
			"https://example.com/page?utm_source=test&utm_campaign=test&utm_medium=test&keep=this",
			"https://example.com/page?keep=this"
		),
		(
			"https://example.com/page?before=1&utm_source=test&after=2",
			"https://example.com/page?before=1&after=2"
		),
		(
			"https://example.com/page?normal=param",
			"https://example.com/page?normal=param"
		),
		(
			"http://example.com/page",
			"https://example.com/page"  # Should be upgraded to HTTPS
		),
		# Test URLs without replacements - should just strip UTM and upgrade to HTTPS
		(
			"https://youtu.be/abc123?utm_source=test",
			"https://youtu.be/abc123"  # Just strip UTM, no URL replacement
		),
		(
			"https://www.youtube.com/watch?v=xyz456&utm_campaign=video",
			"https://www.youtube.com/watch?v=xyz456"  # Just strip UTM, no www. removal
		),
	]

	for input_url, expected_url in test_cases:
		result = canonicalize_url2(input_url, httpsify=True)
		result_str = result.geturl()

		assert result_str == expected_url, \
			f"Failed for {input_url}\n  Expected: {expected_url}\n  Got:      {result_str}"


def test_utm_regex_hyphen_bug():
	"""Test that UTM regex properly handles hyphens in UTM parameter values.

	Bug: utm_regex2 only allows [a-z0-9_]+ for UTM values, but UTM values
	can contain hyphens. This causes partial matches that leave fragments behind.

	This test should PASS when the regex is fixed to include hyphens.
	"""

	# Test the problematic case
	test_url = "https://freddiedeboer.substack.com/p/my-response-to-daniel-bergners-new?utm_source=publication-search"

	# The regex should properly match the FULL UTM parameter including hyphens
	utm_regex2_matches = utm_regex2.findall(test_url)
	expected_full_match = "?utm_source=publication-search"

	# This should match the FULL parameter, not just up to the hyphen
	assert utm_regex2_matches == [expected_full_match], \
		f"utm_regex2 should match the full parameter '{expected_full_match}' but found: {utm_regex2_matches}. This indicates the regex doesn't handle hyphens properly."

	# When we remove the matched UTM parameter, the URL should be clean
	url_after_removal = utm_regex2.sub('', test_url)
	expected_clean_url = "https://freddiedeboer.substack.com/p/my-response-to-daniel-bergners-new"

	assert url_after_removal == expected_clean_url, \
		f"URL should be clean after UTM removal!\n  Original: {test_url}\n  After removal: {url_after_removal}\n  Expected: {expected_clean_url}\n  If this fails, it means URL fragments are left behind due to partial regex matching."