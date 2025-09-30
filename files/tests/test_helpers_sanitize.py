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


def test_allowed_attributes_img_src():
	"""Test allowed_attributes for img tag src."""
	from files.helpers.sanitize import allowed_attributes
	from files.helpers.config.environment import SITE_FULL
	# Relative path
	assert allowed_attributes('img', 'src', '/images/test.jpg') == True
	# Site full path
	assert allowed_attributes('img', 'src', f'{SITE_FULL}/images/test.jpg') == True


def test_allowed_attributes_img_data_src():
	"""Test allowed_attributes for img tag data-src."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('img', 'data-src', '/images/test.jpg') == True


def test_allowed_attributes_img_loading():
	"""Test allowed_attributes for img tag loading attribute."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('img', 'loading', 'lazy') == True
	assert allowed_attributes('img', 'loading', 'eager') == False


def test_allowed_attributes_img_referrpolicy():
	"""Test allowed_attributes for img tag referrpolicy (note the typo in code)."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('img', 'referrpolicy', 'no-referrer') == True
	assert allowed_attributes('img', 'referrpolicy', 'other') == False


def test_allowed_attributes_img_data_bs_toggle():
	"""Test allowed_attributes for img tag data-bs-toggle."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('img', 'data-bs-toggle', 'tooltip') == True
	assert allowed_attributes('img', 'data-bs-toggle', 'modal') == False


def test_allowed_attributes_img_allowed_names():
	"""Test allowed_attributes for img tag allowed attribute names."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('img', 'alt', 'Alt text') == True
	assert allowed_attributes('img', 'title', 'Title text') == True
	assert allowed_attributes('img', 'g', 'value') == True
	assert allowed_attributes('img', 'b', 'value') == True
	assert allowed_attributes('img', 'pat', 'value') == True


def test_allowed_attributes_img_class_pat_hand():
	"""Test allowed_attributes for img tag class pat-hand."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('img', 'class', 'pat-hand') == True
	assert allowed_attributes('img', 'class', 'other-class') == False


def test_allowed_attributes_lite_youtube_params():
	"""Test allowed_attributes for lite-youtube tag params."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('lite-youtube', 'params', 'autoplay=1&modestbranding=1') == True
	assert allowed_attributes('lite-youtube', 'params', 'autoplay=1&modestbranding=1&start=10') == True
	assert allowed_attributes('lite-youtube', 'params', 'other=1') == False


def test_allowed_attributes_lite_youtube_videoid():
	"""Test allowed_attributes for lite-youtube tag videoid."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('lite-youtube', 'videoid', 'dQw4w9WgXcQ') == True


def test_allowed_attributes_lite_youtube_disallowed():
	"""Test allowed_attributes rejects other lite-youtube attributes."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('lite-youtube', 'other', 'value') == False


def test_allowed_attributes_video_controls():
	"""Test allowed_attributes for video tag controls."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('video', 'controls', '') == True
	assert allowed_attributes('video', 'controls', 'true') == False


def test_allowed_attributes_video_preload():
	"""Test allowed_attributes for video tag preload."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('video', 'preload', 'none') == True
	assert allowed_attributes('video', 'preload', 'auto') == False


def test_allowed_attributes_video_disallowed():
	"""Test allowed_attributes rejects other video attributes."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('video', 'autoplay', '') == False


def test_allowed_attributes_source_src_invalid():
	"""Test allowed_attributes for source tag src with invalid URL."""
	from files.helpers.sanitize import allowed_attributes
	# Testing that non-matching patterns return False
	assert allowed_attributes('source', 'src', 'javascript:alert(1)') == False


def test_allowed_attributes_source_disallowed():
	"""Test allowed_attributes rejects other source attributes."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('source', 'type', 'video/mp4') == False


def test_allowed_attributes_p_class_mb_0():
	"""Test allowed_attributes for p tag class mb-0."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('p', 'class', 'mb-0') == True
	assert allowed_attributes('p', 'class', 'other-class') == False


def test_allowed_attributes_p_disallowed():
	"""Test allowed_attributes rejects other p attributes."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('p', 'id', 'myid') == False


def test_allowed_attributes_span_class_pat():
	"""Test allowed_attributes for span tag pat classes."""
	from files.helpers.sanitize import allowed_attributes
	assert allowed_attributes('span', 'class', 'pat-container') == True
	assert allowed_attributes('span', 'class', 'pat-hand') == True
	assert allowed_attributes('span', 'class', 'other-class') == False


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


def test_allowed_attributes_emojis_img_loading():
	"""Test allowed_attributes_emojis for img loading attribute."""
	from files.helpers.sanitize import allowed_attributes_emojis
	assert allowed_attributes_emojis('img', 'loading', 'lazy') == True
	assert allowed_attributes_emojis('img', 'loading', 'eager') == False


def test_allowed_attributes_emojis_img_data_bs_toggle():
	"""Test allowed_attributes_emojis for img data-bs-toggle attribute."""
	from files.helpers.sanitize import allowed_attributes_emojis
	assert allowed_attributes_emojis('img', 'data-bs-toggle', 'tooltip') == True
	assert allowed_attributes_emojis('img', 'data-bs-toggle', 'modal') == False


def test_allowed_attributes_emojis_img_allowed_names():
	"""Test allowed_attributes_emojis for allowed img attribute names."""
	from files.helpers.sanitize import allowed_attributes_emojis
	assert allowed_attributes_emojis('img', 'src', '/e/emoji.webp') == True
	assert allowed_attributes_emojis('img', 'alt', ':emoji:') == True
	assert allowed_attributes_emojis('img', 'title', ':emoji:') == True
	assert allowed_attributes_emojis('img', 'g', 'value') == True


def test_allowed_attributes_emojis_img_disallowed():
	"""Test allowed_attributes_emojis rejects other img attributes."""
	from files.helpers.sanitize import allowed_attributes_emojis
	assert allowed_attributes_emojis('img', 'class', 'myclass') == False
	assert allowed_attributes_emojis('img', 'id', 'myid') == False


def test_allowed_attributes_emojis_other_tags():
	"""Test allowed_attributes_emojis for non-img tags."""
	from files.helpers.sanitize import allowed_attributes_emojis
	assert allowed_attributes_emojis('div', 'class', 'myclass') == False
	assert allowed_attributes_emojis('span', 'style', 'color: red') == False