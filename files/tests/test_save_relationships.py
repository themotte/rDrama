"""Tests for save relationship enforcement (issue #468).

Verifies that SaveRelationship and CommentSaveRelationship models have
proper ORM relationships and that the saved_idlist/saved_comment_idlist
methods correctly filter deleted/removed content.
"""
from . import util_accounts
from . import util
from . import util_submissions
from . import util_comments


def test_save_relationship_has_orm_relationships():
	"""Test that SaveRelationship has user and submission relationships"""
	client, user = util_accounts.create_test_client_and_user()
	post = util_submissions.create_submission_for_client(client)

	from files.__main__ import db_session
	from files.classes import SaveRelationship

	# Save the post
	save_response, _ = util.post_with_formkey(client, f"/save_post/{post.id}", data={})
	assert save_response.status_code == 200

	# Query the save and verify ORM relationships
	save = db_session.query(SaveRelationship).filter_by(
		user_id=user.id, submission_id=post.id
	).one()
	assert save.user is not None
	assert save.user.id == user.id
	assert save.submission is not None
	assert save.submission.id == post.id


def test_comment_save_relationship_has_orm_relationships():
	"""Test that CommentSaveRelationship has user and comment relationships"""
	client, user = util_accounts.create_test_client_and_user()
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	from files.__main__ import db_session
	from files.classes import CommentSaveRelationship

	# Save the comment
	save_response, _ = util.post_with_formkey(client, f"/save_comment/{comment.id}", data={})
	assert save_response.status_code == 200

	# Query the save and verify ORM relationships
	save = db_session.query(CommentSaveRelationship).filter_by(
		user_id=user.id, comment_id=comment.id
	).one()
	assert save.user is not None
	assert save.user.id == user.id
	assert save.comment is not None
	assert save.comment.id == comment.id


def test_submission_has_saves_relationship():
	"""Test that Submission model has a saves relationship"""
	client, user = util_accounts.create_test_client_and_user()
	post = util_submissions.create_submission_for_client(client)

	from files.__main__ import db_session
	from files.classes import Submission

	# Save the post
	save_response, _ = util.post_with_formkey(client, f"/save_post/{post.id}", data={})
	assert save_response.status_code == 200

	# Check the saves relationship on the submission
	db_session.expire_all()
	submission = db_session.query(Submission).filter_by(id=post.id).one()
	assert hasattr(submission, 'saves')
	assert len(submission.saves) == 1
	assert submission.saves[0].user_id == user.id


def test_comment_has_saves_relationship():
	"""Test that Comment model has a saves relationship"""
	client, user = util_accounts.create_test_client_and_user()
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	from files.__main__ import db_session
	from files.classes import Comment

	# Save the comment
	save_response, _ = util.post_with_formkey(client, f"/save_comment/{comment.id}", data={})
	assert save_response.status_code == 200

	# Check the saves relationship on the comment
	db_session.expire_all()
	db_comment = db_session.query(Comment).filter_by(id=comment.id).one()
	assert hasattr(db_comment, 'saves')
	assert len(db_comment.saves) == 1
	assert db_comment.saves[0].user_id == user.id


def test_saved_idlist_excludes_deleted_posts():
	"""Test that saved_idlist filters out user-deleted posts"""
	client, user = util_accounts.create_test_client_and_user()

	# Create and save two posts
	post1 = util_submissions.create_submission_for_client(client)
	post2 = util_submissions.create_submission_for_client(client)

	save1, _ = util.post_with_formkey(client, f"/save_post/{post1.id}", data={})
	assert save1.status_code == 200
	save2, _ = util.post_with_formkey(client, f"/save_post/{post2.id}", data={})
	assert save2.status_code == 200

	from files.__main__ import db_session
	from files.classes import User
	db_session.expire_all()

	# Both posts should appear in saved list
	user_fresh = db_session.query(User).filter_by(id=user.id).one()
	saved_ids = user_fresh.saved_idlist()
	assert post1.id in saved_ids
	assert post2.id in saved_ids

	# Delete post1
	delete_response, _ = util.post_with_formkey(client, f"/delete_post/{post1.id}", data={})
	assert delete_response.status_code == 200

	# post1 should no longer appear in saved list
	db_session.expire_all()
	user_fresh = db_session.query(User).filter_by(id=user.id).one()
	saved_ids = user_fresh.saved_idlist()
	assert post1.id not in saved_ids
	assert post2.id in saved_ids


def test_saved_comment_idlist_excludes_deleted_comments():
	"""Test that saved_comment_idlist filters out user-deleted comments"""
	client, user = util_accounts.create_test_client_and_user()
	post = util_submissions.create_submission_for_client(client)

	# Create and save two comments
	comment1 = util_comments.create_comment_for_client(client, post.id)
	comment2 = util_comments.create_comment_for_client(client, post.id)

	save1, _ = util.post_with_formkey(client, f"/save_comment/{comment1.id}", data={})
	assert save1.status_code == 200
	save2, _ = util.post_with_formkey(client, f"/save_comment/{comment2.id}", data={})
	assert save2.status_code == 200

	from files.__main__ import db_session
	from files.classes import User
	db_session.expire_all()

	# Both comments should appear in saved list
	user_fresh = db_session.query(User).filter_by(id=user.id).one()
	saved_ids = user_fresh.saved_comment_idlist()
	assert comment1.id in saved_ids
	assert comment2.id in saved_ids

	# Delete comment1
	delete_response, _ = util.post_with_formkey(
		client, f"/delete/comment/{comment1.id}", data={}
	)
	assert delete_response.status_code == 200

	# comment1 should no longer appear in saved list
	db_session.expire_all()
	user_fresh = db_session.query(User).filter_by(id=user.id).one()
	saved_ids = user_fresh.saved_comment_idlist()
	assert comment1.id not in saved_ids
	assert comment2.id in saved_ids


def test_saved_idlist_excludes_blocked_user_posts():
	"""Test that saved_idlist filters out posts by blocked users"""
	client1, user1 = util_accounts.create_test_client_and_user("saver-blk")
	client2, user2 = util_accounts.create_test_client_and_user("author-blk")

	# User2 creates a post
	post = util_submissions.create_submission_for_client(client2)

	# User1 saves user2's post
	save_response, _ = util.post_with_formkey(client1, f"/save_post/{post.id}", data={})
	assert save_response.status_code == 200

	from files.__main__ import db_session
	from files.classes import User
	db_session.expire_all()

	# Post should appear in user1's saved list
	user1_fresh = db_session.query(User).filter_by(id=user1.id).one()
	saved_ids = user1_fresh.saved_idlist()
	assert post.id in saved_ids

	# User1 blocks user2
	block_response, _ = util.post_with_formkey(client1, f"/settings/block", data={
		"username": user2.username
	})
	# Block may use a different endpoint; check for the block relationship directly
	from files.classes import UserBlock
	block = UserBlock(user_id=user1.id, target_id=user2.id)
	db_session.add(block)
	db_session.commit()

	# Post by blocked user should no longer appear in saved list
	db_session.expire_all()
	user1_fresh = db_session.query(User).filter_by(id=user1.id).one()
	saved_ids = user1_fresh.saved_idlist()
	assert post.id not in saved_ids


def test_save_relationship_repr():
	"""Test that save relationship models have meaningful repr"""
	from files.classes import SaveRelationship, CommentSaveRelationship

	save = SaveRelationship(user_id=1, submission_id=2)
	assert "user_id=1" in repr(save)
	assert "submission_id=2" in repr(save)

	comment_save = CommentSaveRelationship(user_id=3, comment_id=4)
	assert "user_id=3" in repr(comment_save)
	assert "comment_id=4" in repr(comment_save)
