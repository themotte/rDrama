"""Tests for newtab link handling in content body display.

Covers the _is_external_link and _apply_newtab_settings functions in
files/helpers/content.py, which ensure the user's "Open External Links
In New Tabs" and "Open Internal Links In New Tabs" settings are applied
consistently to links inside rendered post/comment bodies.
"""

import pytest


class TestIsExternalLink:
	"""Tests for _is_external_link helper."""

	def test_empty_href(self):
		from files.helpers.content import _is_external_link
		assert _is_external_link("") is False
		assert _is_external_link(None) is False

	def test_relative_path_is_internal(self):
		from files.helpers.content import _is_external_link
		assert _is_external_link("/post/123") is False
		assert _is_external_link("/search/posts/") is False

	def test_site_full_url_is_internal(self):
		from files.helpers.content import _is_external_link
		from files.helpers.config.environment import SITE_FULL
		assert _is_external_link(f"{SITE_FULL}/post/123") is False

	def test_fragment_is_internal(self):
		from files.helpers.content import _is_external_link
		assert _is_external_link("#section") is False

	def test_external_http_url(self):
		from files.helpers.content import _is_external_link
		assert _is_external_link("https://example.com") is True

	def test_external_different_domain(self):
		from files.helpers.content import _is_external_link
		assert _is_external_link("https://old.reddit.com/r/test") is True

	def test_external_no_scheme(self):
		from files.helpers.content import _is_external_link
		# URLs without scheme but with domain are external
		assert _is_external_link("example.com") is True


class TestApplyNewtabSettings:
	"""Tests for _apply_newtab_settings function."""

	def test_default_settings_no_change(self):
		"""Default settings (newtab=False, newtabexternal=True) should not modify body."""
		from files.helpers.content import _apply_newtab_settings
		body = '<a href="https://example.com" target="_blank" rel="nofollow noopener noreferrer">link</a>'
		result = _apply_newtab_settings(body, newtab=False, newtabexternal=True)
		assert result == body

	def test_newtabexternal_false_removes_target_blank(self):
		"""When newtabexternal=False, target="_blank" should be removed from external links."""
		from files.helpers.content import _apply_newtab_settings
		body = '<a href="https://example.com" target="_blank" rel="nofollow noopener noreferrer">link</a>'
		result = _apply_newtab_settings(body, newtab=False, newtabexternal=False)
		assert 'target="_blank"' not in result
		assert 'href="https://example.com"' in result
		assert 'rel="nofollow noopener noreferrer"' in result

	def test_newtabexternal_false_preserves_internal_links(self):
		"""When newtabexternal=False, internal links should not be affected."""
		from files.helpers.content import _apply_newtab_settings
		body = '<a href="/post/123">internal link</a>'
		result = _apply_newtab_settings(body, newtab=False, newtabexternal=False)
		assert 'target="_blank"' not in result

	def test_newtab_true_adds_target_blank_to_internal(self):
		"""When newtab=True, target="_blank" should be added to internal links."""
		from files.helpers.content import _apply_newtab_settings
		body = '<a href="/post/123">internal link</a>'
		result = _apply_newtab_settings(body, newtab=True, newtabexternal=True)
		assert 'target="_blank"' in result

	def test_newtab_true_does_not_duplicate_target_blank(self):
		"""When newtab=True, should not add duplicate target="_blank" to links that already have it."""
		from files.helpers.content import _apply_newtab_settings
		body = '<a href="https://example.com" target="_blank" rel="nofollow noopener noreferrer">link</a>'
		result = _apply_newtab_settings(body, newtab=True, newtabexternal=True)
		assert result.count('target="_blank"') == 1

	def test_both_settings_off(self):
		"""With newtab=False, newtabexternal=False, no links should have target="_blank"."""
		from files.helpers.content import _apply_newtab_settings
		body = (
			'<a href="/post/123">internal</a> '
			'<a href="https://example.com" target="_blank" rel="nofollow noopener noreferrer">external</a>'
		)
		result = _apply_newtab_settings(body, newtab=False, newtabexternal=False)
		assert 'target="_blank"' not in result

	def test_both_settings_on(self):
		"""With newtab=True, newtabexternal=True, all links should have target="_blank"."""
		from files.helpers.content import _apply_newtab_settings
		body = (
			'<a href="/post/123">internal</a> '
			'<a href="https://example.com" target="_blank" rel="nofollow noopener noreferrer">external</a>'
		)
		result = _apply_newtab_settings(body, newtab=True, newtabexternal=True)
		# Both links should have target="_blank"
		assert result.count('target="_blank"') == 2

	def test_mixed_links_default_external_only(self):
		"""Default settings: only external links have target="_blank"."""
		from files.helpers.content import _apply_newtab_settings
		body = (
			'<a href="/post/123">internal</a> '
			'<a href="https://example.com" target="_blank" rel="nofollow noopener noreferrer">external</a>'
		)
		result = _apply_newtab_settings(body, newtab=False, newtabexternal=True)
		# Should be unchanged from input
		assert result == body

	def test_newtab_true_newtabexternal_false(self):
		"""newtab=True, newtabexternal=False: internal links open in new tab, external don't."""
		from files.helpers.content import _apply_newtab_settings
		body = (
			'<a href="/post/123">internal</a> '
			'<a href="https://example.com" target="_blank" rel="nofollow noopener noreferrer">external</a>'
		)
		result = _apply_newtab_settings(body, newtab=True, newtabexternal=False)
		# Only 1 target="_blank" -- on the internal link
		assert result.count('target="_blank"') == 1
		# Verify it's on the internal link, not the external one
		assert '/post/123" target="_blank"' in result

	def test_multiple_external_links(self):
		"""Multiple external links should all be handled."""
		from files.helpers.content import _apply_newtab_settings
		body = (
			'<a href="https://example.com" target="_blank" rel="nofollow noopener noreferrer">one</a> '
			'<a href="https://other.org" target="_blank" rel="nofollow noopener noreferrer">two</a>'
		)
		result = _apply_newtab_settings(body, newtab=False, newtabexternal=False)
		assert 'target="_blank"' not in result

	def test_links_without_href_unchanged(self):
		"""Anchor tags without href should not be modified."""
		from files.helpers.content import _apply_newtab_settings
		body = '<a name="anchor">section</a>'
		result = _apply_newtab_settings(body, newtab=True, newtabexternal=False)
		assert result == body

	def test_preserves_surrounding_html(self):
		"""Non-link HTML should be preserved."""
		from files.helpers.content import _apply_newtab_settings
		body = '<p>Hello <strong>world</strong></p><a href="https://example.com" target="_blank">link</a><p>end</p>'
		result = _apply_newtab_settings(body, newtab=False, newtabexternal=False)
		assert '<p>Hello <strong>world</strong></p>' in result
		assert '<p>end</p>' in result
		assert 'target="_blank"' not in result

	def test_site_full_url_treated_as_internal(self):
		"""Links using the full site URL should be treated as internal."""
		from files.helpers.content import _apply_newtab_settings
		from files.helpers.config.environment import SITE_FULL
		body = f'<a href="{SITE_FULL}/post/123">site link</a>'
		result = _apply_newtab_settings(body, newtab=True, newtabexternal=True)
		assert 'target="_blank"' in result

	def test_empty_body(self):
		"""Empty body should be returned as-is."""
		from files.helpers.content import _apply_newtab_settings
		assert _apply_newtab_settings("", newtab=True, newtabexternal=False) == ""

	def test_body_without_links(self):
		"""Body without links should be returned as-is."""
		from files.helpers.content import _apply_newtab_settings
		body = "<p>Just some text with no links</p>"
		result = _apply_newtab_settings(body, newtab=True, newtabexternal=False)
		assert result == body
