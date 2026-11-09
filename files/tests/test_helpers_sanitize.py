"""Tests for files/helpers/sanitize.py utility functions."""

import pytest


def test_sanitize_raw_empty_string():
	"""Test sanitize_raw with empty string."""
	from files.helpers.sanitize import sanitize_raw
	result = sanitize_raw("", allow_newlines=False, length_limit=None)
	assert result == ""


def test_sanitize_raw_none():
	"""Test sanitize_raw with None."""
	from files.helpers.sanitize import sanitize_raw
	result = sanitize_raw(None, allow_newlines=False, length_limit=None)
	assert result == ""


def test_sanitize_raw_removes_unwanted_characters():
	"""Test sanitize_raw removes zero-width characters."""
	from files.helpers.sanitize import sanitize_raw
	# \u200e = left-to-right mark, \u200b = zero-width space, \ufeff = zero-width no-break space
	text = "Hello\u200eWorld\u200b!\ufeff"
	result = sanitize_raw(text, allow_newlines=False, length_limit=None)
	assert result == "HelloWorld!"


def test_sanitize_raw_strips_whitespace():
	"""Test sanitize_raw strips leading/trailing whitespace."""
	from files.helpers.sanitize import sanitize_raw
	text = "  Hello World  "
	result = sanitize_raw(text, allow_newlines=False, length_limit=None)
	assert result == "Hello World"


def test_sanitize_raw_removes_newlines():
	"""Test sanitize_raw removes newlines when allow_newlines=False."""
	from files.helpers.sanitize import sanitize_raw
	text = "Hello\nWorld\r\nTest"
	result = sanitize_raw(text, allow_newlines=False, length_limit=None)
	assert result == "HelloWorldTest"


def test_sanitize_raw_converts_newlines():
	"""Test sanitize_raw converts CRLF to LF when allow_newlines=True."""
	from files.helpers.sanitize import sanitize_raw
	text = "Hello\r\nWorld\nTest"
	result = sanitize_raw(text, allow_newlines=True, length_limit=None)
	assert result == "Hello\nWorld\nTest"


def test_sanitize_raw_length_limit():
	"""Test sanitize_raw respects length limit."""
	from files.helpers.sanitize import sanitize_raw
	text = "Hello World"
	result = sanitize_raw(text, allow_newlines=False, length_limit=5)
	assert result == "Hello"


def test_sanitize_raw_length_limit_with_whitespace():
	"""Test sanitize_raw applies length limit after stripping."""
	from files.helpers.sanitize import sanitize_raw
	text = "  Hello World  "
	result = sanitize_raw(text, allow_newlines=False, length_limit=5)
	assert result == "Hello"


def test_allowed_attributes_style():
	"""Test allowed_attributes allows style attribute on any tag."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('div', 'style', 'color: red') == True
	assert allowed_attributes('span', 'style', 'font-weight: bold') == True


def test_allowed_attributes_anchor_href():
	"""Test allowed_attributes for anchor tag href."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('a', 'href', 'https://example.com') == True


def test_allowed_attributes_anchor_rel():
	"""Test allowed_attributes for anchor tag rel attribute."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('a', 'rel', 'nofollow noopener noreferrer') == True
	assert allowed_attributes('a', 'rel', 'other') == False


def test_allowed_attributes_anchor_target():
	"""Test allowed_attributes for anchor tag target attribute."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('a', 'target', '_blank') == True
	assert allowed_attributes('a', 'target', '_self') == False


def test_allowed_attributes_anchor_disallowed():
	"""Test allowed_attributes rejects other anchor attributes."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('a', 'id', 'myid') == False
	assert allowed_attributes('a', 'class', 'myclass') == False


def test_allowed_attributes_p_disallowed():
	"""Test allowed_attributes rejects other p attributes."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('p', 'id', 'myid') == False


def test_allowed_attributes_span_data_bs_toggle():
	"""Test allowed_attributes for span tag data-bs-toggle."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('span', 'data-bs-toggle', 'tooltip') == True
	assert allowed_attributes('span', 'data-bs-toggle', 'modal') == False


def test_allowed_attributes_span_title_and_alt():
	"""Test allowed_attributes for span tag title and alt."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('span', 'title', 'Tooltip text') == True
	assert allowed_attributes('span', 'alt', 'Alt text') == True


def test_allowed_attributes_span_disallowed():
	"""Test allowed_attributes rejects other span attributes."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('span', 'id', 'myid') == False


def test_allowed_attributes_other_tags():
	"""Test allowed_attributes for other tags (should only allow style)."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('div', 'style', 'color: red') == True
	# For tags not explicitly handled, non-style attributes return None (implicitly)
	assert allowed_attributes('div', 'id', 'myid') is None
	assert allowed_attributes('div', 'class', 'myclass') is None


def test_validate_css_valid():
	"""Test validate_css with valid CSS."""
	from files.helpers.sanitize import validate_css
	css = "body { color: red; }"
	valid, msg = validate_css(css)
	assert valid == True
	assert msg == ""


def test_validate_css_closing_style_tag():
	"""Test validate_css rejects closing style tag."""
	from files.helpers.sanitize import validate_css
	css = "body { color: red; } </style>"
	valid, msg = validate_css(css)
	assert valid == False
	assert msg == "Invalid CSS"


def test_validate_css_closing_style_tag_case_insensitive():
	"""Test validate_css rejects closing style tag (case insensitive)."""
	from files.helpers.sanitize import validate_css
	css = "body { color: red; } </STYLE>"
	valid, msg = validate_css(css)
	assert valid == False
	assert msg == "Invalid CSS"


def test_validate_css_import_statement():
	"""Test validate_css rejects @import statements."""
	from files.helpers.sanitize import validate_css
	css = "@import url('https://example.com/style.css');"
	valid, msg = validate_css(css)
	assert valid == False
	assert msg == "@import statements are not allowed"


def test_validate_css_import_statement_case_insensitive():
	"""Test validate_css rejects @import statements (case insensitive)."""
	from files.helpers.sanitize import validate_css
	css = "@IMPORT url('https://example.com/style.css');"
	valid, msg = validate_css(css)
	assert valid == False
	assert msg == "@import statements are not allowed"


def test_validate_css_url_in_background():
	"""Test validate_css rejects external URLs in CSS."""
	from files.helpers.sanitize import validate_css
	css = "body { background: url('https://example.com/image.jpg'); }"
	valid, msg = validate_css(css)
	assert valid == False
	assert msg == "External URL imports are not allowed"


def test_validate_css_url_with_spaces():
	"""Test validate_css rejects external URLs with spaces."""
	from files.helpers.sanitize import validate_css
	css = "body { background: url( 'https://example.com/image.jpg' ); }"
	valid, msg = validate_css(css)
	assert valid == False
	assert msg == "External URL imports are not allowed"
