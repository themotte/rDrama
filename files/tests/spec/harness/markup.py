'''
The markup pages share with the spec, which a reimplementation's pages must carry too. Everything else about a page (its structure, classes, copy and scripts) is the implementation's own.

Spec tests read pages through the helpers below: an element by an id matching one of ELEMENT_IDS or among RULE_ANCHORS (each unique on its page), the counts in ATTRIBUTES, and what standard HTML gives any page (the addresses its links lead to, its form inputs and title, the numbers it holds). `internal/test_spec_hygiene.py` keeps markup out of the tests themselves.
'''
import re

import lxml.html

from files.tests.spec.harness.http import Response

ELEMENT_IDS = {
	"post-<id>": "a post: its entry in listings and on its own page",
	"post-text-<id>": "a listed post's rendered text, hidden until the reader expands it",
	"comment-<id>": "a comment with its replies",
	"context": "on a comment's own page (and a message's conversation page), the comment itself without its ancestors or replies: where the site's links to that page (ending in #context) land",
	"action-<id>": "an entry of the mod log (/log)",
	"stat-<name>": "one figure on /stats (admin/test_site_stats.py)",
	"mod-actions-<id>": "on /admins, how many mod-log entries the admin with that user id made",
	"banned-<id>": "on /banned, the entry of the suspended user with that id",
	"leaderboard-<board>": "one board of /leaderboard, its title and its rows (users/test_leaderboard.py)",
	"mobile-prompt": "the front page's tip to install the site as an app (pages/test_mobile_tip.py)",
}
'''Element ids by pattern: `<id>` is a row id, `<name>` and `<board>` lower-case names.'''

RULE_ANCHORS = ("Contents", "Foundation", "The_Rules", "Courtesy", "Kindness", "Clarity", "Antagonism", "Charity", "Single", "Content", "Effort", "Weakman", "Culture", "Leave", "Multiple", "Engagement", "Disagreement", "Evidence", "Timeouts", "Consensus", "Inclusion", "The_Wildcard_Rule", "Obnoxious", "The_Metarule", "Sentiment")
'''Ids on /rules, each the start of a section or rule: moderators cite rules by these anchors (/rules#Kindness), as the sidebar does.'''

ATTRIBUTES = {
	"data-notification-count": "on every link to the viewer's notifications in the page's header, the viewer's unread count",
	"data-tab-count": "on the tabs of /notifications and /notifications/posts (links to those paths), each tab's unread count",
}

_VARIABLES = {"id": "([1-9][0-9]*)", "name": "([a-z][a-z0-9_-]*)", "board": "([a-z][a-z0-9_-]*)"}
_PATTERNS = {pattern: re.compile(re.sub(r"<([a-z]+)>", lambda m: _VARIABLES[m[1]], pattern)) for pattern in ELEMENT_IDS}


def _check(element_id: str):
	assert element_id in RULE_ANCHORS or any(regex.fullmatch(element_id) for regex in _PATTERNS.values()), f"{element_id!r} matches none of the ids pages share with the spec (ELEMENT_IDS, RULE_ANCHORS)"


def _document(r: Response):
	return lxml.html.document_fromstring(r.text)


def _elements(r: Response, element_id: str) -> list:
	_check(element_id)
	found = _document(r).xpath("//*[@id=$i]", i=element_id)
	assert len(found) <= 1, f"the page has {len(found)} elements with id {element_id!r}"
	return found


def _element(r: Response, element_id: str):
	found = _elements(r, element_id)
	assert found, f"the page has no element with id {element_id!r}"
	return found[0]


def notification_counts(r: Response) -> dict:
	'''
	The unread counts a page shows its logged-in viewer:
	- "bell": the header's notification count;
	- "bell_link": where the bell leads;
	- "all" and "posts": the notification pages' tab counts, None on other pages.

	They're read from the page's ATTRIBUTES.
	'''
	found = {"bell": None, "bell_link": None, "all": None, "posts": None}
	document = _document(r)
	for element in document.xpath("//*[@data-notification-count]"):
		count, link = int(element.get("data-notification-count")), element.get("href")
		assert found["bell"] in (None, count) and found["bell_link"] in (None, link), "the header's bells disagree"
		found["bell"], found["bell_link"] = count, link
	for element in document.xpath("//*[@data-tab-count]"):
		found[{"/notifications": "all", "/notifications/posts": "posts"}[element.get("href")]] = int(element.get("data-tab-count"))
	assert found["bell"] is not None, "the page has no notification bell"
	return found


def element_text(r: Response, element_id: str) -> str:
	'''All the text inside the page's element with the id `element_id`, hidden text included, with runs of whitespace made one space.'''
	return " ".join(_element(r, element_id).text_content().split())


def element_html(r: Response, element_id: str) -> str:
	'''The markup of the page's element with the id `element_id`, the element itself included: for what an element carries outside its text, such as a tooltip.'''
	return lxml.html.tostring(_element(r, element_id), encoding="unicode", with_tail=False)


def has_element(r: Response, element_id: str) -> bool:
	'''Whether the page has an element with the id `element_id`.'''
	return bool(_elements(r, element_id))


def element_values(r: Response, pattern: str) -> list:
	'''The values of the variable in `pattern` (one of ELEMENT_IDS) over the page's elements whose ids match it, in page order; row ids as numbers.'''
	regex = _PATTERNS[pattern]
	matches = [m for m in (regex.fullmatch(element.get("id")) for element in _document(r).xpath("//*[@id]")) if m]
	return [int(m[1]) if "<id>" in pattern else m[1] for m in matches]


def links(r: Response, within: str | None = None) -> list[str]:
	'''The addresses the page's links lead to (every href), in page order; with `within`, only those inside the element with that id.'''
	root = _element(r, within) if within else _document(r)
	return root.xpath(".//@href")


def input_value(r: Response, name: str) -> str | None:
	'''The value of the page's first input named `name`, None if it has none.'''
	found = _document(r).xpath("//input[@name=$n]", n=name)
	return found[0].get("value", "") if found else None


def input_names(r: Response) -> set[str]:
	'''The names of the page's form inputs, selects and text areas.'''
	return set(_document(r).xpath("//input/@name | //select/@name | //textarea/@name"))


def numbers_in(r: Response) -> set[int]:
	'''Every whole number written anywhere in the page, its markup and scripts included.'''
	return {int(n) for n in re.findall(r"\d+", r.text)}


def images_in(html: str) -> list[str]:
	'''The addresses of the images in rendered text (a stored rendering, not a page), in order.'''
	return lxml.html.fragment_fromstring(html, create_parent="div").xpath(".//img/@src") if html.strip() else []


def page_title(r: Response) -> str:
	'''The text of the page's title.'''
	return _document(r).findtext(".//title")
