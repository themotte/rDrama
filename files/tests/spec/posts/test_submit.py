'''
Submitting a post: GET /submit (the form) and POST /submit.

Fields: "title" (required, at most 500 characters), "url" (at most 2048) and/or "body" (at most 500000), "private" (any non-empty value makes the post a draft), "over_18" (any non-empty value marks it 18+), "file" (an image to post instead of a link) and "file2" (up to four images linked at the end of the body).

Browsers get the new post's page; API clients get its JSON. Refusals render the form again with status 400, or for scripts and API clients a JSON error.
'''


import json


import re


from urllib.parse import parse_qs, urlsplit


import pytest


from files.tests.spec.harness import *


def _submit(client, headers=None, files=None, **fields):
	return client.post("/submit", fields, headers=headers, files=files)


def _text_post(**fields):
	return {"title": factories.unique("title"), "body": factories.unique("body"), **fields}


def test_a_link_already_posted_redirects_to_the_earlier_post():
	earlier = factories.post(factories.user(), url="https://example.com/page")

	client = as_user(factories.user())

	with db_diff() as d:
		r = _submit(client, title="t", url="https://example.com/page")

	assert_redirect(r, f"/post/{earlier['id']}/{earlier['title']}")
	d.assert_exactly()


@pytest.mark.parametrize("state", [{"state_mod": "REMOVED"}, {"state_user_deleted_utc": "2020-01-01T00:00:00Z"}], ids=["removed", "deleted"])
def test_links_of_removed_or_deleted_posts_can_be_posted_again(state):
	factories.post(factories.user(), url="https://example.com/page", **state)

	assert_html(_submit(as_user(factories.user()), title="t", url="https://example.com/page"), 200)


def test_resubmitting_an_identical_post_redirects_to_it():
	author = factories.user()
	fields = _text_post()
	assert_html(_submit(as_user(author), **fields), 200)
	earlier = db.rows("submissions")[-1]

	with db_diff() as d:
		r = _submit(as_user(author), **fields)

	assert_redirect(r, f"/post/{earlier['id']}/{fields['title']}")
	d.assert_exactly()


def test_identical_posts_by_different_authors_are_both_accepted():
	fields = _text_post()
	assert_html(_submit(as_user(factories.user()), **fields), 200)

	assert_html(_submit(as_user(factories.user()), **fields), 200)


def _similar_posts(author, count, **fields):
	for _ in range(count):
		factories.post(author, title="buy cheap watches here", body=factories.unique("body"), **fields)


def _image_paths(text):
	return sorted(set(re.findall(r"/images/[^\s\"<>)]+", text)))


TWEET = f"https://twitter.com/someone/status/{123}"
