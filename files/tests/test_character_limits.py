"""Tests for character limit filtering on posts and comments (#559, #704).

Verifies that posts over 50k characters are filtered for non-admin users,
while admins can post without filtering. Also verifies comment character
limit behavior is unchanged.
"""
import string

from . import util_accounts
from . import util_submissions
from . import util_comments
from . import util

from files.__main__ import db_session
from files.classes import Submission, Comment
from files.classes.visstate import StateMod
from files.helpers.config.const import (
	SUBMISSION_BODY_LENGTH_MAXIMUM_UNFILTERED,
	COMMENT_BODY_LENGTH_MAXIMUM_UNFILTERED,
	PERMS,
)


def _make_body(length):
	"""Generate a string of exactly the given length using repeating alphabet."""
	# Use repeating lowercase letters with spaces every 80 chars to form
	# "words" that the sanitizer won't mangle.
	unit = string.ascii_lowercase * 4  # 104 chars
	full = (unit * ((length // len(unit)) + 1))[:length]
	return full


def _submit_post_raw(client, title, body):
	"""Submit a post via the /submit route and return (response, post_id).

	Does NOT assert that body appears in the response text, since very
	large bodies won't render verbatim.
	"""
	response, _ = util.post_with_formkey(
		client, "/submit",
		data={
			"title": title,
			"body": body,
		}
	)
	assert response.status_code == 200, (
		f"Expected 200 from /submit, got {response.status_code}"
	)

	post_info = util.ItemData.from_html(response.text)
	assert post_info is not None, "Could not extract post info from response"
	assert post_info.id_full.startswith('post_')

	post_id = int(post_info.id_full.split('_')[1])
	return response, post_id


# ---- Post character limit tests ----

def test_post_under_50k_not_filtered():
	"""Post with body under 50k chars should NOT be filtered for a normal user."""
	client, user = util_accounts.create_test_client_and_user(name="plen-short")

	body = _make_body(SUBMISSION_BODY_LENGTH_MAXIMUM_UNFILTERED - 100)
	title = util.generate_text()

	_, post_id = _submit_post_raw(client, title, body)

	db_session.expire_all()
	post = db_session.query(Submission).filter_by(id=post_id).first()
	assert post is not None
	assert post.state_mod == StateMod.VISIBLE, (
		f"Post under 50k should be VISIBLE, got {post.state_mod}"
	)


def test_post_exactly_50k_not_filtered():
	"""Post with body of exactly 50k chars should NOT be filtered (boundary test)."""
	client, user = util_accounts.create_test_client_and_user(name="plen-exact")

	body = _make_body(SUBMISSION_BODY_LENGTH_MAXIMUM_UNFILTERED)
	title = util.generate_text()

	_, post_id = _submit_post_raw(client, title, body)

	db_session.expire_all()
	post = db_session.query(Submission).filter_by(id=post_id).first()
	assert post is not None
	assert post.state_mod == StateMod.VISIBLE, (
		f"Post at exactly 50k should be VISIBLE, got {post.state_mod}"
	)


def test_post_over_50k_filtered():
	"""Post with body over 50k chars should be filtered for a normal user."""
	client, user = util_accounts.create_test_client_and_user(name="plen-long")

	body = _make_body(SUBMISSION_BODY_LENGTH_MAXIMUM_UNFILTERED + 1)
	title = util.generate_text()

	_, post_id = _submit_post_raw(client, title, body)

	db_session.expire_all()
	post = db_session.query(Submission).filter_by(id=post_id).first()
	assert post is not None
	assert post.state_mod == StateMod.FILTERED, (
		f"Post over 50k should be FILTERED, got {post.state_mod}"
	)


def test_post_over_50k_admin_not_filtered():
	"""Admin (level 3) can post over 50k without being filtered."""
	client, user = util_accounts.create_test_client_and_admin(
		admin_level=PERMS['POST_COMMENT_MODERATION'] + 1,
		name="plen-admin",
	)

	body = _make_body(SUBMISSION_BODY_LENGTH_MAXIMUM_UNFILTERED + 1)
	title = util.generate_text()

	_, post_id = _submit_post_raw(client, title, body)

	db_session.expire_all()
	post = db_session.query(Submission).filter_by(id=post_id).first()
	assert post is not None
	assert post.state_mod == StateMod.VISIBLE, (
		f"Admin post over 50k should be VISIBLE, got {post.state_mod}"
	)


# ---- Comment character limit regression tests ----

def test_comment_under_50k_not_filtered():
	"""Comment with body under 50k chars should NOT be filtered (regression)."""
	client, user = util_accounts.create_test_client_and_user(name="clen-short")

	post = util_submissions.create_submission_for_client(client)

	body = _make_body(COMMENT_BODY_LENGTH_MAXIMUM_UNFILTERED - 100)
	comment = util_comments.create_comment_for_client(
		client, post.id, data={"body": body}
	)

	db_session.expire_all()
	comment = db_session.query(Comment).filter_by(id=comment.id).first()
	assert comment is not None
	assert comment.state_mod == StateMod.VISIBLE, (
		f"Comment under 50k should be VISIBLE, got {comment.state_mod}"
	)


def test_comment_over_50k_filtered():
	"""Comment with body over 50k chars should be filtered for normal user."""
	client, user = util_accounts.create_test_client_and_user(name="clen-long")

	post = util_submissions.create_submission_for_client(client)

	body = _make_body(COMMENT_BODY_LENGTH_MAXIMUM_UNFILTERED + 1)

	# Submit the comment directly (the helper asserts on response format,
	# but the comment should still be created even when filtered).
	import json
	import re

	response, _ = util.post_with_formkey(
		client, "/comment",
		data={
			"parent_fullname": f'post_{post.id}',
			'parent_level': 1,
			'submission': post.id,
			"body": body,
		}
	)
	assert response.status_code == 200
	data = json.loads(response.text)
	assert 'comment' in data
	match = re.search(r'id="comment-(\d+)"', data['comment'])
	assert match is not None
	comment_id = int(match.group(1))

	db_session.expire_all()
	comment = db_session.query(Comment).filter_by(id=comment_id).first()
	assert comment is not None
	assert comment.state_mod == StateMod.FILTERED, (
		f"Comment over 50k should be FILTERED, got {comment.state_mod}"
	)
