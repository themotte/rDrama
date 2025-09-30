from . import util_accounts
from . import util
from . import util_submissions
from . import util_comments
import time
import json

def test_basic_comment_on_post():
	"""Test basic comment creation on a post"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post to comment on
	post = util_submissions.create_submission_for_client(client)

	# Check no comments exist initially
	from files.__main__ import db_session
	from files.classes import Comment
	initial_comments = db_session.query(Comment).filter_by(parent_submission=post.id).count()
	assert initial_comments == 0

	# Create a comment
	comment_body = util.generate_text()
	comment_response, _ = util.post_with_formkey(
		client, "/comment",
		data={
			"parent_fullname": f"post_{post.id}",
			"body": comment_body,
			"parent_level": 1,
			"submission": post.id
		}
	)

	assert comment_response.status_code == 200
	assert "comment" in comment_response.text

	# Verify comment was created in database
	comments = db_session.query(Comment).filter_by(parent_submission=post.id).all()
	assert len(comments) == 1
	comment = comments[0]
	assert comment.body == comment_body
	assert comment.author_id == user.id
	assert comment.level == 1
	assert comment.parent_comment_id is None

def test_reply_to_comment():
	"""Test replying to an existing comment"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post and initial comment
	post = util_submissions.create_submission_for_client(client)
	parent_comment = util_comments.create_comment_for_client(client, post.id)

	# Reply to the comment
	reply_body = util.generate_text()
	reply_response, _ = util.post_with_formkey(
		client, "/comment",
		data={
			"parent_fullname": f"comment_{parent_comment.id}",
			"body": reply_body,
			"parent_level": 2,
			"submission": post.id
		}
	)

	assert reply_response.status_code == 200

	# Verify reply was created
	from files.__main__ import db_session
	from files.classes import Comment
	reply = db_session.query(Comment).filter_by(parent_comment_id=parent_comment.id).first()
	assert reply is not None
	assert reply.body == reply_body
	assert reply.level == 2
	assert reply.parent_submission == post.id

def test_duplicate_comment_prevention():
	"""Test that duplicate comments are prevented"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post
	post = util_submissions.create_submission_for_client(client)

	# Create a comment
	comment_body = util.generate_text()
	comment_response1, _ = util.post_with_formkey(
		client, "/comment",
		data={
			"parent_fullname": f"post_{post.id}",
			"body": comment_body,
			"parent_level": 1,
			"submission": post.id
		}
	)
	assert comment_response1.status_code == 200

	# Try to create the exact same comment again
	comment_response2, _ = util.post_with_formkey(
		client, "/comment",
		data={
			"parent_fullname": f"post_{post.id}",
			"body": comment_body,
			"parent_level": 1,
			"submission": post.id
		}
	)

	# Should get 409 conflict for duplicate
	assert comment_response2.status_code == 409
	assert "already made that comment" in comment_response2.text

def test_empty_comment_rejection():
	"""Test that empty comments are rejected"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post
	post = util_submissions.create_submission_for_client(client)

	# Try to create an empty comment
	comment_response, _ = util.post_with_formkey(
		client, "/comment",
		data={
			"parent_fullname": f"post_{post.id}",
			"body": "",
			"parent_level": 1,
			"submission": post.id
		}
	)

	assert comment_response.status_code == 400
	assert "actually write something" in comment_response.text

def test_invalid_parent_rejection():
	"""Test that invalid parent references are rejected"""
	client, user = util_accounts.create_test_client_and_user()

	# Try to comment on invalid parent
	comment_response, _ = util.post_with_formkey(
		client, "/comment",
		data={
			"parent_fullname": "invalid_format",
			"body": "test comment",
			"parent_level": 1
		}
	)

	assert comment_response.status_code == 400

def test_comment_auto_upvote():
	"""Test that comments automatically get upvoted by their author"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post and comment
	post = util_submissions.create_submission_for_client(client)
	comment_body = util.generate_text()

	comment_response, _ = util.post_with_formkey(
		client, "/comment",
		data={
			"parent_fullname": f"post_{post.id}",
			"body": comment_body,
			"parent_level": 1,
			"submission": post.id
		}
	)
	assert comment_response.status_code == 200

	# Find the created comment
	from files.__main__ import db_session
	from files.classes import Comment, CommentVote
	comment = db_session.query(Comment).filter_by(parent_submission=post.id, body=comment_body).first()
	assert comment is not None

	# Verify automatic upvote was created
	vote = db_session.query(CommentVote).filter_by(comment_id=comment.id, user_id=user.id).first()
	assert vote is not None
	assert vote.vote_type == 1  # upvote
	assert comment.upvotes == 1

def test_suspended_user_comment_blocked():
	"""Test that suspended users cannot comment"""
	# Just use the default user approach but with a different variable name to avoid test interference
	client, user = util_accounts.create_test_client_and_user("suspend")

	# Create a post first (before suspension)
	post = util_submissions.create_submission_for_client(client)

	# Now suspend the user
	from files.__main__ import db_session
	user.is_banned = 1  # AUTOJANNY_ID or admin id
	user.unban_utc = int(time.time()) + 86400  # 1 day from now
	db_session.add(user)
	db_session.commit()

	# Try to comment while suspended
	comment_response, _ = util.post_with_formkey(
		client, "/comment",
		data={
			"parent_fullname": f"post_{post.id}",
			"body": "test comment",
			"parent_level": 1,
			"submission": post.id
		}
	)

	assert comment_response.status_code == 403

def test_comment_with_over18_flag():
	"""Test comment with over_18 flag inheritance"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a regular post first
	post = util_submissions.create_submission_for_client(client)

	# Then mark it as NSFW
	from files.__main__ import db_session
	post.over_18 = True
	db_session.add(post)
	db_session.commit()

	# Create a comment on the NSFW post
	comment_body = util.generate_text()
	comment_response, _ = util.post_with_formkey(
		client, "/comment",
		data={
			"parent_fullname": f"post_{post.id}",
			"body": comment_body,
			"parent_level": 1,
			"submission": post.id
		}
	)
	assert comment_response.status_code == 200

	# Verify comment inherits over_18 flag
	from files.classes import Comment
	comment = db_session.query(Comment).filter_by(parent_submission=post.id, body=comment_body).first()
	assert comment is not None
	assert comment.over_18 == True

def test_long_comment_filtering():
	"""Test that very long comments get filtered"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post
	post = util_submissions.create_submission_for_client(client)

	# Create a very long comment (longer than COMMENT_BODY_LENGTH_MAXIMUM_UNFILTERED)
	long_body = "x" * 60000  # 60k characters, longer than 50k limit

	comment_response, _ = util.post_with_formkey(
		client, "/comment",
		data={
			"parent_fullname": f"post_{post.id}",
			"body": long_body,
			"parent_level": 1,
			"submission": post.id
		}
	)

	# Should succeed but with a message about pending approval
	assert comment_response.status_code == 200
	response_data = json.loads(comment_response.text)
	assert "pending approval" in response_data.get("message", "")

	# Verify comment was created but filtered
	from files.__main__ import db_session
	from files.classes import Comment
	from files.classes.visstate import StateMod
	comment = db_session.query(Comment).filter_by(parent_submission=post.id).first()
	assert comment is not None
	assert comment.state_mod == StateMod.FILTERED

def test_nonexistent_parent_post():
	"""Test commenting on nonexistent post returns 404"""
	client, user = util_accounts.create_test_client_and_user()

	# Try to comment on nonexistent post - use high ID that won't exist
	comment_response, _ = util.post_with_formkey(
		client, "/comment",
		data={
			"parent_fullname": "post_99999999",
			"body": "test comment",
			"parent_level": 1,
			"submission": 99999999
		}
	)

	assert comment_response.status_code == 404

def test_nonexistent_parent_comment():
	"""Test replying to nonexistent comment returns 404"""
	client, user = util_accounts.create_test_client_and_user()

	# Try to reply to nonexistent comment - use high ID that won't exist
	comment_response, _ = util.post_with_formkey(
		client, "/comment",
		data={
			"parent_fullname": "comment_99999999",
			"body": "test reply",
			"parent_level": 2
		}
	)

	assert comment_response.status_code == 404