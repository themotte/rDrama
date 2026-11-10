'''
Reading pages: the markup pages share with the spec, which a reimplementation's pages must carry too.
'''
from html.parser import HTMLParser

import lxml.html

from files.tests.spec.harness.http import Response


def notification_counts(r: Response) -> dict:
	'''
	The unread counts a page shows its logged-in viewer:
	- "bell": the header's notification count;
	- "bell_link": where the bell leads;
	- "all" and "posts": the notification pages' tab counts, None on other pages.

	They're read from the page's `data-notification-count` (on the bell's link) and `data-tab-count` (on the tab links of /notifications and /notifications/posts) attributes, part of the pages' markup contract.
	'''
	found = {"bell": None, "bell_link": None, "all": None, "posts": None}

	class Parser(HTMLParser):
		def handle_starttag(self, tag, attrs):
			attrs = dict(attrs)
			if "data-notification-count" in attrs:
				count, link = int(attrs["data-notification-count"]), attrs["href"]
				assert found["bell"] in (None, count) and found["bell_link"] in (None, link), "the header's bells disagree"
				found["bell"], found["bell_link"] = count, link
			if "data-tab-count" in attrs:
				found[{"/notifications": "all", "/notifications/posts": "posts"}[attrs["href"]]] = int(attrs["data-tab-count"])

	Parser().feed(r.text)
	assert found["bell"] is not None, "the page has no notification bell"
	return found


_VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


def element_text(r: Response, element_id: str) -> str:
	'''The text a reader sees inside the page's element with the id `element_id` (ids such as "post-<id>" and "comment-<id>" are part of the page contract), with runs of whitespace made one space.'''
	found = {"depth": 0, "seen": False, "text": []}

	class Parser(HTMLParser):
		def handle_starttag(self, tag, attrs):
			if found["depth"]:
				if tag not in _VOID_TAGS: found["depth"] += 1
			elif dict(attrs).get("id") == element_id and not found["seen"]:
				found["seen"] = True
				found["depth"] = 0 if tag in _VOID_TAGS else 1

		def handle_endtag(self, tag):
			if found["depth"] and tag not in _VOID_TAGS: found["depth"] -= 1

		def handle_data(self, data):
			if found["depth"]: found["text"].append(data)

	Parser().feed(r.text)
	assert found["seen"], f"the page has no element with id {element_id!r}"
	return " ".join("".join(found["text"]).split())


def _element(r: Response, element_id: str):
	found = lxml.html.document_fromstring(r.text).xpath("//*[@id=$i]", i=element_id)
	assert found, f"the page has no element with id {element_id!r}"
	return found[0]


def element_html(r: Response, element_id: str) -> str:
	'''The markup of the page's element with the id `element_id`, the element itself included: for what an element carries outside its text, such as a tooltip.'''
	return lxml.html.tostring(_element(r, element_id), encoding="unicode", with_tail=False)


def links(r: Response, within: str | None = None) -> list[str]:
	'''The addresses the page's links lead to (every href), in page order; with `within`, only those inside the element with that id.'''
	root = _element(r, within) if within else lxml.html.document_fromstring(r.text)
	return root.xpath(".//@href")
