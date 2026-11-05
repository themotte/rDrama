'''
Repetitive comments are refused. A comment (POST /comment) or an edit (POST /edit_comment/<comment id>) whose text is too similar to too many of the author's comments from the last 24 hours is refused with 403, and nothing changes.

- New comments: refused once more than 10 of the author's comments from the last day are similar, 20 for accounts at least a day old, 30 for accounts at least a week old. Comments of 10 characters or fewer, and comments from API clients, are never refused as spam.
- Edits: refused once more than 10 similar comments exist, 20 for accounts at least a day old, 30 at least a week old, 40 at least 30 days old.
'''
import time

import pytest

from files.tests.spec.harness import *

SPAM = "buy cheap watches here now"


def _author(age_days):
	author = factories.user()
	db.update("users", {"id": author["id"]}, created_utc=author["created_utc"] - age_days * 86400 - 60)
	return author


def _similar(author, post, count, **overrides):
	for i in range(count):
		factories.comment(author, post, body=f"{SPAM} {i}", **overrides)


def _comment(client, post, body):
	return client.post("/comment", {"parent_fullname": f"post_{post['id']}", "body": body}, headers=XHR)


TIERS = [(0, 10), (1, 20), (7, 30)]


@pytest.mark.parametrize("age_days,threshold", TIERS)
def test_comments_similar_to_too_many_recent_ones_are_refused(age_days, threshold):
	author, post = _author(age_days), factories.post(factories.user())
	_similar(author, post, threshold + 1)
	client = as_user(author)

	with db_diff() as d:
		r = _comment(client, post, f"{SPAM} again")

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("age_days,threshold", TIERS)
def test_comments_similar_to_up_to_the_threshold_are_accepted(age_days, threshold):
	author, post = _author(age_days), factories.post(factories.user())
	_similar(author, post, threshold)

	r = _comment(as_user(author), post, f"{SPAM} again")

	assert_status(r, 200)


def test_similar_comments_older_than_a_day_dont_count():
	author, post = _author(0), factories.post(factories.user())
	_similar(author, post, 11, created_utc=int(time.time()) - 86400 - 60)

	r = _comment(as_user(author), post, f"{SPAM} again")

	assert_status(r, 200)


def test_short_comments_are_never_spam():
	author, post = _author(0), factories.post(factories.user())
	for i in range(11):
		factories.comment(author, post, body=f"short {i}")

	r = _comment(as_user(author), post, "short x")

	assert_status(r, 200)


def test_api_clients_comments_are_never_spam():
	author, post = _author(0), factories.post(factories.user())
	_similar(author, post, 11)

	r = _comment(as_api(factories.api_token(author)), post, f"{SPAM} again")

	assert_status(r, 200)


EDIT_TIERS = [(0, 10), (1, 20), (7, 30), (30, 40)]


@pytest.mark.parametrize("age_days,threshold", EDIT_TIERS)
def test_edits_similar_to_too_many_recent_comments_are_refused(age_days, threshold):
	author, post = _author(age_days), factories.post(factories.user())
	_similar(author, post, threshold + 1)
	target = factories.comment(author, post, body=factories.unique())
	client = as_user(author)

	with db_diff() as d:
		r = client.post(f"/edit_comment/{target['id']}", {"body": f"{SPAM} again"}, headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("age_days,threshold", EDIT_TIERS)
def test_edits_similar_to_up_to_the_threshold_are_accepted(age_days, threshold):
	author, post = _author(age_days), factories.post(factories.user())
	_similar(author, post, threshold)
	target = factories.comment(author, post, body=factories.unique())

	r = as_user(author).post(f"/edit_comment/{target['id']}", {"body": f"{SPAM} again"}, headers=XHR)

	assert_status(r, 200)


def test_similar_comments_older_than_a_day_dont_count_against_edits():
	author, post = _author(0), factories.post(factories.user())
	_similar(author, post, 11, created_utc=int(time.time()) - 86400 - 60)
	target = factories.comment(author, post, body=factories.unique())

	r = as_user(author).post(f"/edit_comment/{target['id']}", {"body": f"{SPAM} again"}, headers=XHR)

	assert_status(r, 200)
