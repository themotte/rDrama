import pytest
from files.helpers.content import canonicalize_url2


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