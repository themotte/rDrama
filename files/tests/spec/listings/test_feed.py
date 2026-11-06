'''
The site's feed (GET /rss, also /feed) lists what the front page shows a logged-out visitor, including posts without text.
'''
from files.tests.spec.harness import *


def test_the_feed_lists_posts_without_text():
	link = factories.post(factories.user(), url="https://example.com/a")
	text = factories.post(factories.user(), body="some text")

	r = anon().get("/rss")

	assert_status(r, 200)
	assert_in_payload(r, link["title"])
	assert_in_payload(r, text["title"])
