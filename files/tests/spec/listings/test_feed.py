'''
The site's feed (GET /rss, also /feed) lists what the front page shows a logged-out visitor, including posts without text, whoever asks: users and API clients get the same feed. GET /rss/<sort>/<t> takes the front page's "sort" and "t" from the path instead (a "sort" query parameter is ignored); the others use "new" and "all".

It's an Atom feed (Content-Type application/xml). Each post is an entry: its title; its permalink as both id and link; its author's name, and as the author's URI their profile (/@<name>, relative to the entry's xml:base); a media:thumbnail; and, for a post with text, the rendered text as HTML content (posts with only a link have none). Its times are RFC 3339 in UTC ("2024-05-06T07:08:09Z"): the feed's "updated" is the time of the request, an entry's "published" is when the post was made, and its "updated" is when it was last edited, or when it was made if it never was.
'''
import re
import time
import xml.etree.ElementTree as ET

from urllib.parse import urljoin

import pytest

from files.tests.spec.harness import *

ATOM = "{http://www.w3.org/2005/Atom}"
XML_BASE = "{http://www.w3.org/XML/1998/namespace}base"


def _atom_time(epoch: int) -> str:
	return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def _entry(feed, post) -> ET.Element:
	return next(e for e in feed.findall("{*}entry") if e.findtext("{*}title") == post["title"])


def _feed(r) -> ET.Element:
	return ET.fromstring(r.body)


def _titles(r) -> list[str]:
	return [e.findtext("{*}title") for e in _feed(r).findall("{*}entry")]


def test_the_feed_lists_posts_without_text():
	link = factories.post(factories.user(), url="https://example.com/a")
	text = factories.post(factories.user(), body="some text")

	r = anon().get("/rss")

	assert_status(r, 200)
	assert_in_payload(r, link["title"])
	assert_in_payload(r, text["title"])


def test_entry_times_are_when_the_post_was_made_and_last_edited():
	made, edited = 1_700_000_000, 1_700_003_600
	plain = factories.post(factories.user(), created_utc=made)
	changed = factories.post(factories.user(), created_utc=made, edited_utc=edited)

	feed = ET.fromstring(anon().get("/rss").body)

	assert (_entry(feed, plain).findtext("{*}published"), _entry(feed, plain).findtext("{*}updated")) == (_atom_time(made), _atom_time(made))
	assert (_entry(feed, changed).findtext("{*}published"), _entry(feed, changed).findtext("{*}updated")) == (_atom_time(made), _atom_time(edited))


def test_the_feed_is_updated_as_of_the_request():
	before = int(time.time())
	updated = ET.fromstring(anon().get("/rss").body).findtext("{*}updated")

	assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", updated), updated
	assert _atom_time(before) <= updated <= _atom_time(int(time.time()))


def test_feed_is_the_same_feed():
	post = factories.post(factories.user())

	assert _titles(anon().get("/feed")) == _titles(anon().get("/rss")) and post["title"] in _titles(anon().get("/feed"))


@pytest.mark.parametrize("client", [lambda author: as_user(author), lambda author: as_api(factories.api_token(author))], ids=["user", "API client"])
def test_everyone_gets_the_visitors_feed(client):
	author = factories.user()
	draft = factories.post(author, private=True)
	shown = factories.post(factories.user())

	r = client(author).get("/rss")

	assert_status(r, 200)
	assert shown["title"] in _titles(r) and draft["title"] not in _titles(r)


def test_sort_and_time_come_from_the_path():
	older = factories.post(factories.user(), created_utc=int(time.time()) - 3600)
	newer = factories.post(factories.user())

	by_path = _titles(anon().get("/rss/old/all"))
	by_query = _titles(anon().get("/rss", params={"sort": "old"}))

	assert by_path.index(older["title"]) < by_path.index(newer["title"])
	assert by_query.index(newer["title"]) < by_query.index(older["title"])


def test_the_feed_is_atom_served_as_xml():
	r = anon().get("/rss")

	assert r.header("Content-Type").split(";")[0] == "application/xml"
	assert _feed(r).tag == f"{ATOM}feed"


def test_an_entry_names_the_post_its_author_and_links_both():
	author = factories.user()
	post = factories.post(author, body="some text")

	entry = _entry(_feed(anon().get("/rss")), post)

	link = entry.find("{*}link").get("href")
	assert entry.findtext("{*}id") == link and link.startswith(f"{config.site_url()}/post/{post['id']}")
	assert entry.findtext("{*}author/{*}name") == author["username"]
	assert urljoin(entry.get(XML_BASE), entry.findtext("{*}author/{*}uri")) == f"{config.site_url()}/@{author['username']}"


def test_text_posts_carry_their_text_and_every_post_a_thumbnail():
	token = factories.unique("text")
	text = factories.post(factories.user(), body=token)
	link = factories.post(factories.user(), url="https://example.com/a")

	feed = _feed(anon().get("/rss"))

	assert token in _entry(feed, text).findtext("{*}content")
	assert _entry(feed, link).find("{*}content") is None
	assert all(_entry(feed, p).find("{*}thumbnail").get("url") for p in (text, link))
