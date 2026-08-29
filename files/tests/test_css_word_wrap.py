"""Tests that long-word wrapping CSS rules are present in main.css.

Regression test for https://github.com/themotte/rDrama/issues/190:
extremely long words (URLs, unbroken strings) must wrap in comment bodies,
post bodies, and preview containers to prevent horizontal overflow.
"""
import os

CSS_PATH = os.path.join(
	os.path.dirname(__file__), "..", "assets", "css", "main.css"
)


def _read_css():
	with open(CSS_PATH) as f:
		return f.read()


def _get_rule_block(css, selector):
	"""Extract the content of a CSS rule block for the given selector.

	Returns the text between { and the matching } for the first occurrence
	of `selector` in the CSS. Returns None if not found.
	"""
	idx = css.find(selector)
	if idx == -1:
		return None
	brace_start = css.find("{", idx)
	if brace_start == -1:
		return None
	depth = 1
	i = brace_start + 1
	while i < len(css) and depth > 0:
		if css[i] == "{":
			depth += 1
		elif css[i] == "}":
			depth -= 1
		i += 1
	return css[brace_start + 1 : i - 1]


def test_comment_text_has_word_break():
	"""Comment text containers must wrap long words."""
	css = _read_css()
	block = _get_rule_block(css, ".comment .comment-body .comment-text")
	assert block is not None, "selector .comment .comment-body .comment-text not found"
	assert "word-break" in block
	assert "overflow-wrap" in block


def test_post_body_has_word_break():
	"""Post body containers must wrap long words."""
	css = _read_css()
	block = _get_rule_block(css, ".post-body")
	assert block is not None, "selector .post-body not found"
	assert "word-break" in block
	assert "overflow-wrap" in block


def test_comment_body_has_min_width_zero():
	"""Comment body grid item needs min-width: 0 to prevent grid overflow."""
	css = _read_css()
	block = _get_rule_block(css, ".comment-body {")
	assert block is not None, "selector .comment-body not found"
	assert "min-width" in block


def test_form_preview_has_word_break():
	"""Comment form preview containers must wrap long words."""
	css = _read_css()
	block = _get_rule_block(
		css, '.comment-section div[id^="form-preview-"]'
	)
	assert block is not None, "form-preview selector not found"
	assert "word-break" in block
	assert "overflow-wrap" in block


def test_preview_has_word_break():
	"""Generic preview containers must wrap long words."""
	css = _read_css()
	block = _get_rule_block(css, ".preview {")
	assert block is not None, "selector .preview not found"
	assert "word-break" in block
	assert "overflow-wrap" in block
