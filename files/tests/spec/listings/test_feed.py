'''
The site's feed (GET /rss, also /feed) lists what the front page shows a logged-out visitor, including posts without text.

It's an Atom feed. Its times are RFC 3339 in UTC ("2024-05-06T07:08:09Z"): the feed's "updated" is the time of the request, an entry's "published" is when the post was made, and its "updated" is when it was last edited, or when it was made if it never was.
'''
import re
import time
import xml.etree.ElementTree as ET

from files.tests.spec.harness import *

def _atom_time(epoch: int) -> str:
	return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def _entry(feed, post) -> ET.Element:
	return next(e for e in feed.findall("{*}entry") if e.findtext("{*}title") == post["title"])


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
