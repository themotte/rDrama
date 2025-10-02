"""Tests for comment CRUD operations (create, read, update, delete)."""
from . import util_accounts
from . import util
from . import util_submissions
from . import util_comments

from files.__main__ import db_session
from files.classes import Comment


def test_delete_comment():
	"""Test deleting a comment"""
	client, user = util_accounts.create_test_client_and_user("del-comment")

	# Create a post and comment
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	# Verify comment exists and is not deleted
	assert comment.state_user_deleted_utc is None

	# Delete the comment
	delete_response, _ = util.post_with_formkey(
		client, f"/delete/comment/{comment.id}",
		data={}
	)

	assert delete_response.status_code == 200
	assert "deleted" in delete_response.text.lower()

	# Verify comment is marked as deleted in database
	comment_after = db_session.get(Comment, comment.id)
	assert comment_after.state_user_deleted_utc is not None


def test_delete_comment_not_author():
	"""Test that non-authors cannot delete comments"""
	client1, user1 = util_accounts.create_test_client_and_user("author-del")
	client2, user2 = util_accounts.create_test_client_and_user("other-del")

	# User 1 creates a post and comment
	post = util_submissions.create_submission_for_client(client1)
	comment = util_comments.create_comment_for_client(client1, post.id)

	# User 2 tries to delete user 1's comment
	delete_response, _ = util.post_with_formkey(
		client2, f"/delete/comment/{comment.id}",
		data={}
	)

	assert delete_response.status_code == 403


def test_delete_already_deleted_comment():
	"""Test that deleting an already deleted comment returns 409"""
	client, user = util_accounts.create_test_client_and_user("double-del")

	# Create a post and comment
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	# Delete the comment once
	delete_response1, _ = util.post_with_formkey(
		client, f"/delete/comment/{comment.id}",
		data={}
	)
	assert delete_response1.status_code == 200

	# Try to delete again
	delete_response2, _ = util.post_with_formkey(
		client, f"/delete/comment/{comment.id}",
		data={}
	)

	assert delete_response2.status_code == 409


def test_undelete_comment():
	"""Test undeleting a deleted comment"""
	client, user = util_accounts.create_test_client_and_user("undel-comment")

	# Create a post and comment
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	# Delete the comment
	delete_response, _ = util.post_with_formkey(
		client, f"/delete/comment/{comment.id}",
		data={}
	)
	assert delete_response.status_code == 200

	# Undelete the comment
	undelete_response, _ = util.post_with_formkey(
		client, f"/undelete/comment/{comment.id}",
		data={}
	)

	assert undelete_response.status_code == 200
	assert "undeleted" in undelete_response.text.lower()

	# Verify comment is no longer deleted
	comment_after = db_session.get(Comment, comment.id)
	assert comment_after.state_user_deleted_utc is None


def test_undelete_not_deleted_comment():
	"""Test that undeleting a non-deleted comment returns 409"""
	client, user = util_accounts.create_test_client_and_user("undel-notdel")

	# Create a post and comment
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	# Try to undelete a non-deleted comment
	undelete_response, _ = util.post_with_formkey(
		client, f"/undelete/comment/{comment.id}",
		data={}
	)

	assert undelete_response.status_code == 409


def test_edit_comment():
	"""Test editing a comment"""
	client, user = util_accounts.create_test_client_and_user("edit-comment")

	# Create a post and comment
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	original_body = comment.body
	new_body = util.generate_text()

	# Edit the comment
	edit_response, _ = util.post_with_formkey(
		client, f"/edit_comment/{comment.id}",
		data={"body": new_body}
	)

	assert edit_response.status_code == 200

	# Verify comment body was updated
	comment_after = db_session.get(Comment, comment.id)
	assert comment_after.body == new_body
	assert comment_after.body != original_body


def test_edit_comment_not_author():
	"""Test that non-authors cannot edit comments"""
	client1, user1 = util_accounts.create_test_client_and_user("author-edit")
	client2, user2 = util_accounts.create_test_client_and_user("other-edit")

	# User 1 creates a post and comment
	post = util_submissions.create_submission_for_client(client1)
	comment = util_comments.create_comment_for_client(client1, post.id)

	# User 2 tries to edit user 1's comment
	edit_response, _ = util.post_with_formkey(
		client2, f"/edit_comment/{comment.id}",
		data={"body": "new text"}
	)

	assert edit_response.status_code == 403


def test_edit_comment_empty_body():
	"""Test that editing to empty body is rejected"""
	client, user = util_accounts.create_test_client_and_user("edit-empty-test")

	# Create a post and comment
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	# Try to edit with empty body
	edit_response, _ = util.post_with_formkey(
		client, f"/edit_comment/{comment.id}",
		data={"body": ""}
	)

	assert edit_response.status_code == 400
	assert "type something" in edit_response.text.lower()


def test_pin_comment():
	"""Test pinning a comment on your own post"""
	client, user = util_accounts.create_test_client_and_user("pin-comment")

	# Create a post and comment on it
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	# Verify comment is not pinned
	assert comment.is_pinned is None

	# Pin the comment
	pin_response, _ = util.post_with_formkey(
		client, f"/pin_comment/{comment.id}",
		data={}
	)

	assert pin_response.status_code == 200
	assert "pinned" in pin_response.text.lower()

	# Verify comment is pinned
	comment_after = db_session.get(Comment, comment.id)
	assert comment_after.is_pinned is not None
	assert "(OP)" in comment_after.is_pinned or user.username in comment_after.is_pinned


def test_pin_comment_not_op():
	"""Test that non-OP cannot pin comments"""
	client1, user1 = util_accounts.create_test_client_and_user("author-pin")
	client2, user2 = util_accounts.create_test_client_and_user("commenter-pin")

	# User 1 creates a post
	post = util_submissions.create_submission_for_client(client1)

	# User 2 creates a comment on user 1's post
	comment = util_comments.create_comment_for_client(client2, post.id)

	# User 2 tries to pin their own comment (but they're not OP)
	pin_response, _ = util.post_with_formkey(
		client2, f"/pin_comment/{comment.id}",
		data={}
	)

	assert pin_response.status_code == 403


def test_unpin_comment():
	"""Test unpinning a pinned comment"""
	client, user = util_accounts.create_test_client_and_user("unpin-comment")

	# Create a post and comment
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	# Pin the comment
	pin_response, _ = util.post_with_formkey(
		client, f"/pin_comment/{comment.id}",
		data={}
	)
	assert pin_response.status_code == 200

	# Unpin the comment
	unpin_response, _ = util.post_with_formkey(
		client, f"/unpin_comment/{comment.id}",
		data={}
	)

	assert unpin_response.status_code == 200
	assert "unpinned" in unpin_response.text.lower()

	# Verify comment is no longer pinned
	comment_after = db_session.get(Comment, comment.id)
	assert comment_after.is_pinned is None


def test_save_comment():
	"""Test saving a comment"""
	client, user = util_accounts.create_test_client_and_user("save-comment")

	# Create a post and comment
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	# Save the comment
	save_response, _ = util.post_with_formkey(
		client, f"/save_comment/{comment.id}",
		data={}
	)

	assert save_response.status_code == 200
	assert "saved" in save_response.text.lower()

	# Verify save relationship exists in database
	from files.classes import CommentSaveRelationship
	save_rel = db_session.query(CommentSaveRelationship).filter_by(
		user_id=user.id,
		comment_id=comment.id
	).one_or_none()

	assert save_rel is not None


def test_save_already_saved_comment():
	"""Test that saving an already saved comment is idempotent"""
	client, user = util_accounts.create_test_client_and_user("double-save")

	# Create a post and comment
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	# Save the comment twice
	save_response1, _ = util.post_with_formkey(
		client, f"/save_comment/{comment.id}",
		data={}
	)
	assert save_response1.status_code == 200

	save_response2, _ = util.post_with_formkey(
		client, f"/save_comment/{comment.id}",
		data={}
	)

	# Should still succeed (idempotent)
	assert save_response2.status_code == 200


def test_unsave_comment():
	"""Test unsaving a saved comment"""
	client, user = util_accounts.create_test_client_and_user("unsave-comment")

	# Create a post and comment
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	# Save the comment
	save_response, _ = util.post_with_formkey(
		client, f"/save_comment/{comment.id}",
		data={}
	)
	assert save_response.status_code == 200

	# Unsave the comment
	unsave_response, _ = util.post_with_formkey(
		client, f"/unsave_comment/{comment.id}",
		data={}
	)

	assert unsave_response.status_code == 200
	assert "unsaved" in unsave_response.text.lower()

	# Verify save relationship no longer exists
	from files.classes import CommentSaveRelationship
	save_rel = db_session.query(CommentSaveRelationship).filter_by(
		user_id=user.id,
		comment_id=comment.id
	).one_or_none()

	assert save_rel is None


def test_unsave_not_saved_comment():
	"""Test that unsaving a non-saved comment is idempotent"""
	client, user = util_accounts.create_test_client_and_user("unsave-notsav")

	# Create a post and comment
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	# Unsave a comment that was never saved
	unsave_response, _ = util.post_with_formkey(
		client, f"/unsave_comment/{comment.id}",
		data={}
	)

	# Should still succeed (idempotent)
	assert unsave_response.status_code == 200
