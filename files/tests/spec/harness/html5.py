'''
Pages and stored markup as browsers read them: parsed by the HTML standard's algorithm (lexbor's), with scripting off, so what a `<noscript>` holds is read as markup. The result is an lxml.html tree, for the harness's readers.

An lxml tree can't hold everything HTML can, so the conversion changes what it must: characters XML forbids, in names, text, attribute values and comments, become U+FFFD (as does a comment's "--"), but a form feed, which HTML counts as whitespace, becomes a space; an element whose tag name lxml still refuses is kept, with its contents, under the tag `invalid`. Elements of SVG and MathML get their bare tag names. A template's contents aren't in the tree, as they aren't in a browser's document until a script puts them there.
'''
import re

import lxml.html
from lxml import etree
from selectolax.lexbor import LexborHTMLParser

_NOT_XML = re.compile("[\x00-\x08\x0b\x0e-\x1f\ufffe\uffff\ud800-\udfff]")
_COMMENT_UNSAFE = re.compile("--|-$")


def _xml(text: str) -> str:
	return _NOT_XML.sub("\ufffd", text.replace("\x0c", " "))


def document(text: str):
	'''The `<html>` element of a page.'''
	return _element(LexborHTMLParser(text).root)


def fragment(text: str):
	'''A `<div>` holding `text` as markup read inside an element (a stored rendering, say).'''
	div = lxml.html.Element("div")
	first = LexborHTMLParser(text, is_fragment=True, fragment_tag="div").root
	_append_children(div, first)
	return div


def _element(node):
	try:
		element = lxml.html.Element(_xml(node.tag))
	except ValueError:
		element = lxml.html.Element("invalid")
	for name, value in node.attributes.items():
		element.set(_xml(name), _xml(value or ""))
	_append_children(element, node.child)
	return element


def _append_children(parent, node):
	'''Appends `node` and its following siblings to `parent`.'''
	last = None
	while node is not None:
		if node.is_text_node:
			text = _xml(node.text_content or "")
			if last is None:
				parent.text = (parent.text or "") + text
			else:
				last.tail = (last.tail or "") + text
		else:
			child = _comment(node) if node.is_comment_node or node.tag is None else _element(node) if node.is_element_node else None
			if child is not None:
				parent.append(child)
				last = child
		node = node.next


def _comment(node):
	'''A comment, or what the standard reads as one (`<?…>`, which lexbor keeps as a processing instruction).'''
	content = node.comment_content if node.is_comment_node else "?" + (node.html or "").removeprefix("<?").removesuffix("?>")
	return etree.Comment(_COMMENT_UNSAFE.sub(lambda m: m[0].replace("-", "\ufffd"), _xml(content or "")))
