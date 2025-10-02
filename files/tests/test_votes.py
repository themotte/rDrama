from . import util_accounts
from . import util
from . import util_submissions
from . import util_comments

def test_vote_post_upvote():
	"""Test upvoting a post"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post to vote on
	post = util_submissions.create_submission_for_client(client)

	# Check initial state - posts start with 1 upvote (author's vote)
	from files.__main__ import db_session
	from files.classes import Vote
	initial_votes = db_session.query(Vote).filter_by(submission_id=post.id, user_id=user.id).count()
	assert initial_votes == 1
	assert post.upvotes == 1

	# Upvote the post (should be idempotent since already upvoted)
	vote_response, _ = util.post_with_formkey(client, f"/vote/post/{post.id}/1", data={})

	assert vote_response.status_code == 204

	# Verify the vote was recorded (should still be 1 vote, idempotent)
	db_session.expire_all()
	votes = db_session.query(Vote).filter_by(submission_id=post.id, user_id=user.id).all()
	assert len(votes) == 1
	assert votes[0].vote_type == 1

	# Verify post upvote count unchanged (idempotent)
	from files.classes import Submission
	post_updated = db_session.query(Submission).filter_by(id=post.id).first()
	assert post_updated.upvotes == 1

def test_vote_post_downvote():
	"""Test downvoting a post (if downvotes are enabled)"""
	from files.helpers.config.environment import ENABLE_DOWNVOTES
	if not ENABLE_DOWNVOTES:
		return  # Skip if downvotes are disabled

	client, user = util_accounts.create_test_client_and_user()

	# Create a post to vote on
	post = util_submissions.create_submission_for_client(client)

	# Check initial state - post has author's upvote
	from files.__main__ import db_session
	from files.classes import Vote, Submission
	assert post.downvotes == 0

	# Downvote the post (changes from upvote to downvote)
	vote_response, _ = util.post_with_formkey(client, f"/vote/post/{post.id}/-1", data={})

	assert vote_response.status_code == 204

	# Verify the vote was recorded
	db_session.expire_all()
	votes = db_session.query(Vote).filter_by(submission_id=post.id, user_id=user.id).all()
	assert len(votes) == 1
	assert votes[0].vote_type == -1

	# Verify post vote counts changed
	post_updated = db_session.query(Submission).filter_by(id=post.id).first()
	assert post_updated.upvotes == 0
	assert post_updated.downvotes == 1

def test_vote_post_remove_vote():
	"""Test removing a vote from a post"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post (already has author's upvote)
	post = util_submissions.create_submission_for_client(client)

	from files.__main__ import db_session
	from files.classes import Vote, Submission
	assert post.upvotes == 1

	# Remove the vote (set to 0)
	vote_response, _ = util.post_with_formkey(client, f"/vote/post/{post.id}/0", data={})

	assert vote_response.status_code == 204

	# Verify the vote was updated
	db_session.expire_all()
	votes = db_session.query(Vote).filter_by(submission_id=post.id, user_id=user.id).all()
	assert len(votes) == 1
	assert votes[0].vote_type == 0

	# Verify post upvote count decreased
	post_updated = db_session.query(Submission).filter_by(id=post.id).first()
	assert post_updated.upvotes == 0

def test_vote_post_change_vote():
	"""Test changing a vote on a post"""
	from files.helpers.config.environment import ENABLE_DOWNVOTES
	if not ENABLE_DOWNVOTES:
		return  # Skip if downvotes are disabled

	client, user = util_accounts.create_test_client_and_user()

	# Create a post (already has author's upvote)
	post = util_submissions.create_submission_for_client(client)

	from files.__main__ import db_session
	from files.classes import Vote, Submission
	assert post.upvotes == 1
	assert post.downvotes == 0

	# Change to downvote
	vote_response, _ = util.post_with_formkey(client, f"/vote/post/{post.id}/-1", data={})

	assert vote_response.status_code == 204

	# Verify the vote was updated
	db_session.expire_all()
	votes = db_session.query(Vote).filter_by(submission_id=post.id, user_id=user.id).all()
	assert len(votes) == 1
	assert votes[0].vote_type == -1

	# Verify vote counts changed
	post_updated = db_session.query(Submission).filter_by(id=post.id).first()
	assert post_updated.upvotes == 0
	assert post_updated.downvotes == 1

def test_vote_post_same_vote_twice():
	"""Test that voting the same way twice is idempotent"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post (already has author's upvote)
	post = util_submissions.create_submission_for_client(client)

	from files.__main__ import db_session
	from files.classes import Submission
	assert post.upvotes == 1

	# Try to upvote again (should be idempotent)
	vote_response, _ = util.post_with_formkey(client, f"/vote/post/{post.id}/1", data={})

	assert vote_response.status_code == 204

	# Verify upvote count didn't change
	db_session.expire_all()
	post_updated = db_session.query(Submission).filter_by(id=post.id).first()
	assert post_updated.upvotes == 1

def test_vote_post_invalid_value():
	"""Test that invalid vote values are rejected"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post
	post = util_submissions.create_submission_for_client(client)

	# Try to vote with invalid value
	vote_response, _ = util.post_with_formkey(client, f"/vote/post/{post.id}/5", data={})

	assert vote_response.status_code == 400

def test_vote_post_nonexistent():
	"""Test voting on a nonexistent post returns 404"""
	client, user = util_accounts.create_test_client_and_user()

	# Try to vote on a nonexistent post
	vote_response, _ = util.post_with_formkey(client, "/vote/post/999999/1", data={})

	assert vote_response.status_code == 404

def test_vote_comment_upvote():
	"""Test upvoting a comment"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post and comment
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	# Check initial state - comments start with 1 upvote (author's vote)
	from files.__main__ import db_session
	from files.classes import CommentVote, Comment
	initial_votes = db_session.query(CommentVote).filter_by(comment_id=comment.id, user_id=user.id).count()
	assert initial_votes == 1
	assert comment.upvotes == 1

	# Upvote the comment (should be idempotent since already upvoted)
	vote_response, _ = util.post_with_formkey(client, f"/vote/comment/{comment.id}/1", data={})

	assert vote_response.status_code == 204

	# Verify the vote was recorded (should still be 1 vote, idempotent)
	db_session.expire_all()
	votes = db_session.query(CommentVote).filter_by(comment_id=comment.id, user_id=user.id).all()
	assert len(votes) == 1
	assert votes[0].vote_type == 1

	# Verify comment upvote count unchanged (idempotent)
	comment_updated = db_session.query(Comment).filter_by(id=comment.id).first()
	assert comment_updated.upvotes == 1

def test_vote_comment_downvote():
	"""Test downvoting a comment (if downvotes are enabled)"""
	from files.helpers.config.environment import ENABLE_DOWNVOTES
	if not ENABLE_DOWNVOTES:
		return  # Skip if downvotes are disabled

	client, user = util_accounts.create_test_client_and_user()

	# Create a post and comment
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	# Check initial state - comment has author's upvote
	from files.__main__ import db_session
	from files.classes import CommentVote, Comment
	assert comment.downvotes == 0

	# Downvote the comment (changes from upvote to downvote)
	vote_response, _ = util.post_with_formkey(client, f"/vote/comment/{comment.id}/-1", data={})

	assert vote_response.status_code == 204

	# Verify the vote was recorded
	db_session.expire_all()
	votes = db_session.query(CommentVote).filter_by(comment_id=comment.id, user_id=user.id).all()
	assert len(votes) == 1
	assert votes[0].vote_type == -1

	# Verify comment vote counts changed
	comment_updated = db_session.query(Comment).filter_by(id=comment.id).first()
	assert comment_updated.upvotes == 0
	assert comment_updated.downvotes == 1

def test_vote_comment_remove_vote():
	"""Test removing a vote from a comment"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post and comment (already has author's upvote)
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	from files.__main__ import db_session
	from files.classes import CommentVote, Comment
	assert comment.upvotes == 1

	# Remove the vote (set to 0)
	vote_response, _ = util.post_with_formkey(client, f"/vote/comment/{comment.id}/0", data={})

	assert vote_response.status_code == 204

	# Verify the vote was updated
	db_session.expire_all()
	votes = db_session.query(CommentVote).filter_by(comment_id=comment.id, user_id=user.id).all()
	assert len(votes) == 1
	assert votes[0].vote_type == 0

	# Verify comment upvote count decreased
	comment_updated = db_session.query(Comment).filter_by(id=comment.id).first()
	assert comment_updated.upvotes == 0

def test_vote_comment_change_vote():
	"""Test changing a vote on a comment"""
	from files.helpers.config.environment import ENABLE_DOWNVOTES
	if not ENABLE_DOWNVOTES:
		return  # Skip if downvotes are disabled

	client, user = util_accounts.create_test_client_and_user()

	# Create a post and comment (already has author's upvote)
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	from files.__main__ import db_session
	from files.classes import CommentVote, Comment
	assert comment.upvotes == 1
	assert comment.downvotes == 0

	# Change to downvote
	vote_response, _ = util.post_with_formkey(client, f"/vote/comment/{comment.id}/-1", data={})

	assert vote_response.status_code == 204

	# Verify the vote was updated
	db_session.expire_all()
	votes = db_session.query(CommentVote).filter_by(comment_id=comment.id, user_id=user.id).all()
	assert len(votes) == 1
	assert votes[0].vote_type == -1

	# Verify vote counts changed
	comment_updated = db_session.query(Comment).filter_by(id=comment.id).first()
	assert comment_updated.upvotes == 0
	assert comment_updated.downvotes == 1

def test_vote_comment_same_vote_twice():
	"""Test that voting the same way twice on a comment is idempotent"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post and comment (already has author's upvote)
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	from files.__main__ import db_session
	from files.classes import Comment
	assert comment.upvotes == 1

	# Try to upvote again (should be idempotent)
	vote_response, _ = util.post_with_formkey(client, f"/vote/comment/{comment.id}/1", data={})

	assert vote_response.status_code == 204

	# Verify upvote count didn't change
	db_session.expire_all()
	comment_updated = db_session.query(Comment).filter_by(id=comment.id).first()
	assert comment_updated.upvotes == 1

def test_vote_comment_invalid_value():
	"""Test that invalid vote values are rejected for comments"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post and comment
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	# Try to vote with invalid value
	vote_response, _ = util.post_with_formkey(client, f"/vote/comment/{comment.id}/5", data={})

	assert vote_response.status_code == 400

def test_vote_comment_nonexistent():
	"""Test voting on a nonexistent comment returns 404"""
	client, user = util_accounts.create_test_client_and_user()

	# Try to vote on a nonexistent comment
	vote_response, _ = util.post_with_formkey(client, "/vote/comment/999999/1", data={})

	assert vote_response.status_code == 404


def test_vote_post_by_other_user():
	"""Test voting on another user's post updates their coins and truescore"""
	# Create two users
	client1, user1 = util_accounts.create_test_client_and_user(name="voter1")
	client2, user2 = util_accounts.create_test_client_and_user(name="author1")

	# User2 creates a post
	post = util_submissions.create_submission_for_client(client2)

	from files.__main__ import db_session
	from files.classes import User, Submission

	# Get user2's initial coins and truescore
	db_session.expire_all()
	user2_before = db_session.query(User).filter_by(id=user2.id).first()
	initial_coins = user2_before.coins
	initial_truescore = user2_before.truescore

	# User1 upvotes user2's post
	vote_response, _ = util.post_with_formkey(client1, f"/vote/post/{post.id}/1", data={})
	assert vote_response.status_code == 204

	# Verify user2's coins and truescore increased by 1
	db_session.expire_all()
	user2_after = db_session.query(User).filter_by(id=user2.id).first()
	assert user2_after.coins == initial_coins + 1
	assert user2_after.truescore == initial_truescore + 1

	# User1 changes to downvote (if enabled)
	from files.helpers.config.environment import ENABLE_DOWNVOTES
	if ENABLE_DOWNVOTES:
		vote_response, _ = util.post_with_formkey(client1, f"/vote/post/{post.id}/-1", data={})
		assert vote_response.status_code == 204

		# Verify user2's coins and truescore decreased by 2 (removed +1, added -1)
		db_session.expire_all()
		user2_after = db_session.query(User).filter_by(id=user2.id).first()
		assert user2_after.coins == initial_coins - 1
		assert user2_after.truescore == initial_truescore - 1


def test_vote_comment_by_other_user():
	"""Test voting on another user's comment updates their coins and truescore"""
	# Create two users
	client1, user1 = util_accounts.create_test_client_and_user(name="voter2")
	client2, user2 = util_accounts.create_test_client_and_user(name="author2")

	# User2 creates a post and comment
	post = util_submissions.create_submission_for_client(client2)
	comment = util_comments.create_comment_for_client(client2, post.id)

	from files.__main__ import db_session
	from files.classes import User, Comment

	# Get user2's initial coins and truescore
	db_session.expire_all()
	user2_before = db_session.query(User).filter_by(id=user2.id).first()
	initial_coins = user2_before.coins
	initial_truescore = user2_before.truescore

	# User1 upvotes user2's comment
	vote_response, _ = util.post_with_formkey(client1, f"/vote/comment/{comment.id}/1", data={})
	assert vote_response.status_code == 204

	# Verify user2's coins and truescore increased by 1
	db_session.expire_all()
	user2_after = db_session.query(User).filter_by(id=user2.id).first()
	assert user2_after.coins == initial_coins + 1
	assert user2_after.truescore == initial_truescore + 1

	# User1 changes to downvote (if enabled)
	from files.helpers.config.environment import ENABLE_DOWNVOTES
	if ENABLE_DOWNVOTES:
		vote_response, _ = util.post_with_formkey(client1, f"/vote/comment/{comment.id}/-1", data={})
		assert vote_response.status_code == 204

		# Verify user2's coins and truescore decreased by 2 (removed +1, added -1)
		db_session.expire_all()
		user2_after = db_session.query(User).filter_by(id=user2.id).first()
		assert user2_after.coins == initial_coins - 1
		assert user2_after.truescore == initial_truescore - 1


def test_admin_vote_info_get_no_link():
	"""Test admin vote info page without link parameter"""
	from files.__main__ import db_session
	from files.classes import User

	# Create an admin user (admin_level >= 3)
	client, user = util_accounts.create_test_client_and_admin(3, name="admin1")

	# Access the vote info page without a link
	response = client.get("/votes")
	assert response.status_code == 200


def test_admin_vote_info_get_with_post():
	"""Test admin vote info page with post link"""
	from files.__main__ import db_session
	from files.classes import User

	# Create an admin user
	admin_client, admin_user = util_accounts.create_test_client_and_admin(3, name="admin2")

	# Create a regular user and a post
	client, user = util_accounts.create_test_client_and_user(name="poster1")
	post = util_submissions.create_submission_for_client(client)

	# Access the vote info page with post link
	response = admin_client.get(f"/votes?link=post_{post.id}")
	assert response.status_code == 200


def test_admin_vote_info_get_with_comment():
	"""Test admin vote info page with comment link"""
	from files.__main__ import db_session
	from files.classes import User

	# Create an admin user
	admin_client, admin_user = util_accounts.create_test_client_and_admin(3, name="admin3")

	# Create a regular user, post, and comment
	client, user = util_accounts.create_test_client_and_user(name="commenter1")
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	# Access the vote info page with comment link
	response = admin_client.get(f"/votes?link=comment_{comment.id}")
	assert response.status_code == 200


def test_admin_vote_info_invalid_link():
	"""Test admin vote info page with invalid link format"""
	from files.__main__ import db_session
	from files.classes import User

	# Create an admin user
	admin_client, admin_user = util_accounts.create_test_client_and_admin(3, name="admin4")

	# Access with invalid link format
	response = admin_client.get("/votes?link=invalid_format")
	assert response.status_code == 400


def test_admin_vote_info_nonexistent_post():
	"""Test admin vote info page with nonexistent post"""
	from files.__main__ import db_session
	from files.classes import User

	# Create an admin user
	admin_client, admin_user = util_accounts.create_test_client_and_admin(3, name="admin5")

	# Access with nonexistent post (get_post raises exception, caught and returns 400)
	response = admin_client.get("/votes?link=post_999999")
	assert response.status_code == 400


def test_admin_vote_info_nonexistent_comment():
	"""Test admin vote info page with nonexistent comment"""
	from files.__main__ import db_session
	from files.classes import User

	# Create an admin user
	admin_client, admin_user = util_accounts.create_test_client_and_admin(3, name="admin6")

	# Access with nonexistent comment (get_comment raises exception, caught and returns 400)
	response = admin_client.get("/votes?link=comment_999999")
	assert response.status_code == 400


def test_admin_vote_info_requires_admin():
	"""Test that vote info page requires admin access"""
	# Create a regular user (not admin)
	client, user = util_accounts.create_test_client_and_user(name="regular1")

	# Try to access the vote info page
	response = client.get("/votes")
	# Should redirect to login or show 403
	assert response.status_code in [302, 403]