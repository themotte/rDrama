from . import util_accounts
from . import util
from . import util_submissions
from . import util_comments

def test_report_post():
	"""Test reporting a post"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post to report
	post = util_submissions.create_submission_for_client(client)

	# Check that no flags exist initially
	from files.__main__ import db_session
	from files.classes import Flag
	initial_flags = db_session.query(Flag).filter_by(post_id=post.id, user_id=user.id).count()
	assert initial_flags == 0

	# Report the post
	report_response, _ = util.post_with_formkey(
		client, f"/report/post/{post.id}",
		data={
			"reason": "Test report reason"
		}
	)

	assert report_response.status_code == 200
	assert "Post reported!" in report_response.text

	# Verify the flag was created in the database
	flags = db_session.query(Flag).filter_by(post_id=post.id, user_id=user.id).all()
	assert len(flags) == 1
	assert flags[0].reason == "Test report reason"

def test_report_post_with_admin_flair():
	"""Test that admin users can set flair when reporting with ! prefix"""
	client, user = util_accounts.create_test_client_and_admin(2, "admin")

	# Make user an admin (admin_level >= 2)
	from files.__main__ import db_session
	from files.classes import Submission, ModAction

	# Create a post to report
	post = util_submissions.create_submission_for_client(client)

	# Check initial state
	original_flair = post.flair
	initial_mod_actions = db_session.query(ModAction).filter_by(target_submission_id=post.id, kind="flair_post").count()

	# Report with flair (! prefix)
	flair_text = "test-flair"
	report_response, _ = util.post_with_formkey(
		client, f"/report/post/{post.id}",
		data={
			"reason": f"!{flair_text}"
		}
	)

	assert report_response.status_code == 200
	assert "Post reported!" in report_response.text

	# Verify the flair was set in the database
	updated_post = db_session.query(Submission).filter_by(id=post.id).first()
	assert updated_post.flair == flair_text

	# Verify a mod action was created
	mod_actions = db_session.query(ModAction).filter_by(target_submission_id=post.id, kind="flair_post").all()
	assert len(mod_actions) == initial_mod_actions + 1
	assert mod_actions[-1].user_id == user.id
	assert f'"{flair_text}"' in mod_actions[-1]._note

def test_report_comment():
	"""Test reporting a comment"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post and comment to report
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	# Check that no flags exist initially
	from files.__main__ import db_session
	from files.classes import CommentFlag
	initial_flags = db_session.query(CommentFlag).filter_by(comment_id=comment.id, user_id=user.id).count()
	assert initial_flags == 0

	# Report the comment
	report_response, _ = util.post_with_formkey(
		client, f"/report/comment/{comment.id}",
		data={
			"reason": "Test comment report"
		}
	)

	assert report_response.status_code == 200
	assert "Comment reported!" in report_response.text

	# Verify the flag was created in the database
	flags = db_session.query(CommentFlag).filter_by(comment_id=comment.id, user_id=user.id).all()
	assert len(flags) == 1
	assert flags[0].reason == "Test comment report"

def test_report_nonexistent_post():
	"""Test reporting a nonexistent post returns 404"""
	client, user = util_accounts.create_test_client_and_user()

	# Try to report a nonexistent post
	report_response, _ = util.post_with_formkey(
		client, "/report/post/999999",
		data={
			"reason": "Test report"
		}
	)

	assert report_response.status_code == 404

def test_report_nonexistent_comment():
	"""Test reporting a nonexistent comment returns 404"""
	client, user = util_accounts.create_test_client_and_user()

	# Try to report a nonexistent comment
	report_response, _ = util.post_with_formkey(
		client, "/report/comment/999999",
		data={
			"reason": "Test report"
		}
	)

	assert report_response.status_code == 404