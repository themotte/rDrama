'''
Edits are checked for spam (spec/comments/test_spam.py) against the comment spam settings, COMMENT_SPAM_SIMILAR_THRESHOLD and COMMENT_SPAM_COUNT_THRESHOLD, as new comments are, not the post ones. The spec runs with both pairs equal; this sets them apart.
'''
import pytest

from files.__main__ import app
from files.tests.spec.harness import XHR, as_user, assert_status, factories

SPAM = "buy cheap watches here now"


@pytest.fixture
def comment_threshold_lower(monkeypatch):
	monkeypatch.setitem(app.config, "COMMENT_SPAM_COUNT_THRESHOLD", 2)
	monkeypatch.setitem(app.config, "SPAM_SIMILAR_COUNT_THRESHOLD", 100)


@pytest.fixture
def post_threshold_lower(monkeypatch):
	monkeypatch.setitem(app.config, "COMMENT_SPAM_COUNT_THRESHOLD", 100)
	monkeypatch.setitem(app.config, "SPAM_SIMILAR_COUNT_THRESHOLD", 2)


def _edit_after_similar(count):
	author, post = factories.user(), factories.post(factories.user())
	for i in range(count):
		factories.comment(author, post, body=f"{SPAM} {i}")
	target = factories.comment(author, post, body=factories.unique())
	return as_user(author).post(f"/edit_comment/{target['id']}", {"body": f"{SPAM} again"}, headers=XHR)


def test_an_edit_past_the_comment_threshold_is_refused(comment_threshold_lower):
	assert_status(_edit_after_similar(3), 403)


def test_an_edit_past_only_the_post_threshold_is_accepted(post_threshold_lower):
	assert_status(_edit_after_similar(3), 200)


@pytest.fixture
def only_the_post_similarity_matches(monkeypatch):
	monkeypatch.setitem(app.config, "COMMENT_SPAM_COUNT_THRESHOLD", 2)
	monkeypatch.setitem(app.config, "SPAM_SIMILAR_COUNT_THRESHOLD", 2)
	monkeypatch.setitem(app.config, "COMMENT_SPAM_SIMILAR_THRESHOLD", 0.0)
	monkeypatch.setitem(app.config, "SPAM_SIMILARITY_THRESHOLD", 1.01)


@pytest.fixture
def only_the_comment_similarity_matches(monkeypatch):
	monkeypatch.setitem(app.config, "COMMENT_SPAM_COUNT_THRESHOLD", 2)
	monkeypatch.setitem(app.config, "SPAM_SIMILAR_COUNT_THRESHOLD", 2)
	monkeypatch.setitem(app.config, "COMMENT_SPAM_SIMILAR_THRESHOLD", 1.01)
	monkeypatch.setitem(app.config, "SPAM_SIMILARITY_THRESHOLD", 0.0)


def test_an_edit_similar_by_the_comment_measure_is_refused(only_the_comment_similarity_matches):
	assert_status(_edit_after_similar(3), 403)


def test_an_edit_similar_only_by_the_post_measure_is_accepted(only_the_post_similarity_matches):
	assert_status(_edit_after_similar(3), 200)
