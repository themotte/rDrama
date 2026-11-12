'''The harness reads markup as the HTML standard parses it (spec/harness/html5.py), into lxml trees holding what lxml can.'''
import lxml.html
import pytest

from files.tests.spec.harness import html5


def _body(page: str) -> str:
	body = html5.document(page).find("body")
	return (body.text or "") + "".join(lxml.html.tostring(child, encoding="unicode") for child in body)


def _fragment(markup: str) -> str:
	return lxml.html.tostring(html5.fragment(markup), encoding="unicode")


@pytest.mark.parametrize("page, body", [
	# Text directly inside a table is moved before it, and rows get a body
	("<table>x<tr><td>a</td></tr></table>", "x<table><tbody><tr><td>a</td></tr></tbody></table>"),
	# Misnested formatting is reopened inside the paragraph
	("<b>x<p>y</b>z", "<b>x</b><p><b>y</b>z</p>"),
	# A pre's first newline isn't its text
	("<pre>\n\nx</pre>", "<pre>\nx</pre>"),
	# A form inside a form is no form
	("<form action='/a'><form action='/b'><input></form>", '<form action="/a"><input></form>'),
	# An image inside a select is kept
	("<select><img src='/i'></select>", '<select><img src="/i"></select>'),
], ids=["table text", "misnested", "pre", "nested forms", "select"])
def test_pages_are_parsed_as_the_standard_says(page, body):
	assert _body(page) == body


def test_a_fragment_is_read_inside_an_element():
	assert _fragment("lead<b>x</b>tail<tr><td>z</td></tr>") == "<div>lead<b>x</b>tailz</div>"


def test_characters_xml_forbids_become_replacement_characters():
	tree = html5.document("<p title='a\x0bb' a\x01b=1>&#1;\x01\ufffe</p><q\x01>x</q\x01>")

	p = tree.find(".//p")
	assert p.text == "\ufffd\ufffd\ufffd" and dict(p.attrib) == {"title": "a\ufffdb", "a\ufffdb": "1"}
	assert [element.text for element in tree.iter("q\ufffd")] == ["x"]


def test_a_form_feed_is_whitespace():
	assert html5.fragment("a\x0cb").text == "a b"


def test_attributes_keep_their_names_and_svgs_their_case():
	tree = html5.document("<svg viewBox='0 0 1 1'><a xlink:href='/s'></a></svg><p ,=1 class=c>")

	assert tree.find(".//svg").get("viewBox") == "0 0 1 1"
	assert dict(tree.find(".//svg/a").attrib) == {"xlink:href": "/s"}
	assert dict(tree.find(".//p").attrib) == {",": "1", "class": "c"}


def test_an_element_whose_tag_lxml_refuses_keeps_its_contents():
	assert _body('<a"b>x<i>y</i></a"b>') == "<invalid>x<i>y</i></invalid>"


def test_comments_are_kept_and_template_contents_are_not():
	# lxml holds no "--" in a comment; "<?…>" is a comment too
	tree = html5.document("<p>a<!--x--y-->b<?pi x>c</p><template><a href='/t'></a></template>")

	p = tree.find(".//p")
	assert [node.text for node in p] == ["x\ufffd\ufffdy", "?pi x"] and p.text == "a" and [node.tail for node in p] == ["b", "c"]
	assert tree.xpath("//@href") == []


def test_noscript_holds_markup():
	assert html5.document("<noscript><a href='/n'>n</a></noscript>").xpath("//@href") == ["/n"]
