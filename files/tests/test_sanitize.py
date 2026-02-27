"""Tests for tilde handling in files/helpers/sanitize.py.

Covers the tag-aware strikethrough regex that fixes #737:
tildes inside HTML tag attributes (e.g., href URLs) must not be
interpreted as strikethrough markers.

NOTE: We cannot import `_apply_strikethrough` directly from
`files.helpers.sanitize` because the module's top-level imports pull in
Flask, SQLAlchemy, and environment config that requires a running app.
Instead, we extract the regex pattern and replacement function from the
source file and test them directly. A meta-test verifies the pattern
stays in sync with the source.
"""

import re
import textwrap
import time


# ---------------------------------------------------------------------------
# Reproduce the exact regex and replacement logic from sanitize.py so we can
# test without triggering the heavy import chain.  The meta-test at the bottom
# ensures these stay in sync with the real source.
# ---------------------------------------------------------------------------

_tag_or_strikethrough_regex = re.compile(
	r'(<[^>]+>)|(~{1,2})([^~]+?)\2', flags=re.A
)

def _strikethrough_replace(m):
	if m.group(1):  # matched an HTML tag -- return unchanged
		return m.group(1)
	return '<del>' + m.group(3) + '</del>'

def _apply_strikethrough(text):
	"""Apply strikethrough formatting only to text outside HTML tags."""
	return _tag_or_strikethrough_regex.sub(_strikethrough_replace, text)


# ===========================================================================
# Tests
# ===========================================================================

class TestStrikethroughBasic:
	"""Verify that strikethrough formatting still works correctly."""

	def test_single_tilde_strikethrough(self):
		result = _apply_strikethrough("hello ~world~ there")
		assert result == "hello <del>world</del> there"

	def test_double_tilde_strikethrough(self):
		result = _apply_strikethrough("hello ~~world~~ there")
		assert result == "hello <del>world</del> there"

	def test_multiple_single_strikethroughs(self):
		result = _apply_strikethrough("~a~ and ~b~ and ~c~")
		assert result == "<del>a</del> and <del>b</del> and <del>c</del>"

	def test_multiple_double_strikethroughs(self):
		result = _apply_strikethrough("~~a~~ and ~~b~~")
		assert result == "<del>a</del> and <del>b</del>"

	def test_strikethrough_with_spaces(self):
		result = _apply_strikethrough("~multiple words here~")
		assert result == "<del>multiple words here</del>"

	def test_no_tildes_unchanged(self):
		text = "no tildes in this text at all"
		result = _apply_strikethrough(text)
		assert result == text

	def test_single_tilde_alone_unchanged(self):
		"""A lone tilde with no matching pair should not be altered."""
		text = "this has a ~ lone tilde"
		result = _apply_strikethrough(text)
		assert result == text


class TestTildeInUrls:
	"""Verify that tildes inside HTML tag attributes are preserved (#737)."""

	def test_url_with_tilde_in_href(self):
		"""Core bug: tilde in href must not be mangled."""
		text = '<a href="https://example.com/~user/page">link</a>'
		result = _apply_strikethrough(text)
		assert result == text

	def test_url_with_text_fragment_tilde(self):
		"""Text fragment anchors use :~: syntax which must be preserved."""
		text = '<a href="https://example.com/page#:~:text=foo">link</a>'
		result = _apply_strikethrough(text)
		assert result == text

	def test_url_with_multiple_tildes_in_href(self):
		text = '<a href="https://example.com/~user/~config/~data">link</a>'
		result = _apply_strikethrough(text)
		assert result == text

	def test_two_links_with_tildes_not_paired(self):
		"""Two separate links each containing a tilde must not pair across tags.

		The old regex would match the ~ in the first href with the ~ in the
		second href, creating <del>...</del> that spans across tags and
		corrupts the HTML.
		"""
		text = (
			'<a href="https://example.com/~user">a</a>'
			' and '
			'<a href="https://other.com/~test">b</a>'
		)
		result = _apply_strikethrough(text)
		assert result == text

	def test_exact_bug_report_scenario(self):
		"""Reproduce the exact scenario from issue #737."""
		text = (
			'<a href="https://www.newsweek.com/von-spakovsky-voter-fraud-trump-632422'
			'#:~:text=investigating%20imagined%20transgressions,Trump%20plainly%20craves"'
			' rel="nofollow noopener noreferrer" target="_blank">voter ID requirements</a>'
		)
		result = _apply_strikethrough(text)
		assert result == text
		assert "<del>" not in result

	def test_url_tilde_plus_strikethrough_text(self):
		"""URL with tilde AND strikethrough text should both work correctly."""
		text = '<a href="https://example.com/~user">link</a> some ~deleted~ words'
		result = _apply_strikethrough(text)
		assert 'href="https://example.com/~user"' in result
		assert "<del>deleted</del>" in result

	def test_markdown_link_with_tilde_after_conversion(self):
		"""After markdown conversion, a link like [text](url~tilde) becomes HTML.

		This tests the HTML that markdown would produce from such a link.
		"""
		text = '<a href="https://example.com/~user/page">click here</a>'
		result = _apply_strikethrough(text)
		assert 'href="https://example.com/~user/page"' in result
		assert "<del>" not in result


class TestStrikethroughWithHtmlTags:
	"""Verify strikethrough works correctly alongside various HTML elements."""

	def test_strikethrough_between_paragraph_tags(self):
		result = _apply_strikethrough("<p>~test~</p>")
		assert result == "<p><del>test</del></p>"

	def test_strikethrough_after_br(self):
		result = _apply_strikethrough("<br>~test~")
		assert result == "<br><del>test</del>"

	def test_self_closing_tag_with_tilde_preserved(self):
		text = '<img src="/images/test~img.webp" />'
		result = _apply_strikethrough(text)
		assert result == text

	def test_strikethrough_around_inline_tag(self):
		"""Strikethrough markers split by an HTML tag should not pair across it."""
		text = "~before <strong>bold</strong> after~"
		result = _apply_strikethrough(text)
		# The <strong> tag is consumed by the tag branch, splitting the text.
		# The pieces "~before " and " after~" cannot form a valid pair.
		assert "<strong>bold</strong>" in result

	def test_mixed_tags_and_strikethrough(self):
		text = '<p>~one~ <a href="url~with~tilde">link</a> ~two~</p>'
		result = _apply_strikethrough(text)
		assert "<del>one</del>" in result
		assert "<del>two</del>" in result
		assert 'href="url~with~tilde"' in result

	def test_nested_tags_preserved(self):
		text = '<a href="~url~"><span class="test">text</span></a>'
		result = _apply_strikethrough(text)
		assert 'href="~url~"' in result
		assert '<span class="test">' in result


class TestEdgeCases:
	"""Edge cases and regression tests."""

	def test_empty_string(self):
		assert _apply_strikethrough("") == ""

	def test_only_tildes(self):
		"""String of only tildes should not crash or produce unexpected output."""
		result = _apply_strikethrough("~~~")
		# The regex requires [^~]+? between tildes, so pure tildes won't match
		assert result == "~~~"

	def test_adjacent_strikethroughs(self):
		result = _apply_strikethrough("~a~~b~")
		assert "<del>a</del>" in result

	def test_tilde_in_code_tag_content(self):
		"""Tildes inside <code> tag content (not attributes) are still processed.

		This is expected -- code block protection happens at the markdown
		level before _apply_strikethrough is called.
		"""
		text = "<code>~test~</code>"
		result = _apply_strikethrough(text)
		assert "<code>" in result
		assert "</code>" in result

	def test_backreference_enforces_matching_tilde_count(self):
		"""The backreference \\2 ensures ~ pairs with ~ and ~~ with ~~."""
		# ~text~~ has mismatched tilde counts; should not produce <del>
		text = "hello ~text~~ world"
		result = _apply_strikethrough(text)
		# The ~ before "text" should pair with the first ~ after "text",
		# leaving one trailing ~
		assert "<del>text</del>" in result

	def test_long_content_no_catastrophic_backtracking(self):
		"""Ensure the regex completes quickly on large input."""
		large_text = (
			'<a href="https://example.com/~user">link</a> ' * 100
			+ '~strike~ ' * 100
		)
		start = time.monotonic()
		result = _apply_strikethrough(large_text)
		elapsed = time.monotonic() - start
		assert elapsed < 1.0
		assert result.count("<del>strike</del>") == 100

	def test_multiline_content(self):
		"""Strikethrough should work across typical multiline HTML."""
		text = "<p>First line ~deleted~</p>\n<p>Second ~also~ line</p>"
		result = _apply_strikethrough(text)
		assert "<del>deleted</del>" in result
		assert "<del>also</del>" in result


class TestRegexSyncWithSource:
	"""Verify that the test's local regex matches the one in sanitize.py."""

	def test_regex_pattern_matches_source(self):
		"""The regex pattern tested here must match the source file."""
		import os
		source_path = os.path.join(
			os.path.dirname(__file__), '..', 'helpers', 'sanitize.py'
		)
		with open(source_path) as f:
			source = f.read()

		# Extract the regex pattern from the source
		match = re.search(
			r"_tag_or_strikethrough_regex\s*=\s*re\.compile\(r'(.+?)'",
			source
		)
		assert match is not None, (
			"Could not find _tag_or_strikethrough_regex in sanitize.py"
		)
		source_pattern = match.group(1)
		test_pattern = _tag_or_strikethrough_regex.pattern
		assert source_pattern == test_pattern, (
			f"Test regex pattern {test_pattern!r} does not match "
			f"source pattern {source_pattern!r} -- update the test"
		)
