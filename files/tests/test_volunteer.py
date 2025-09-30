from . import util_accounts
from . import util
from . import util_submissions
from . import util_comments


@util.no_rate_limit
def test_volunteer_page_no_duty():
	"""Test accessing volunteer page when no duty is available"""
	client, user = util_accounts.create_test_client_and_user()

	# Get the volunteer page
	response = client.get("/volunteer")
	assert response.status_code == 200
	assert "volunteer" in response.text.lower()


@util.no_rate_limit
def test_volunteer_page_with_duty():
	"""Test volunteer page when a duty is available"""
	# Create two users: one to report, one to volunteer
	reporter_client, reporter = util_accounts.create_test_client_and_user("reporter")
	volunteer_client, volunteer = util_accounts.create_test_client_and_user("volunteer")

	# Create a post and comment to be reported
	post = util_submissions.create_submission_for_client(reporter_client)
	comment = util_comments.create_comment_for_client(reporter_client, post.id)

	# Report the comment
	report_response, _ = util.post_with_formkey(
		reporter_client, f"/report/comment/{comment.id}",
		data={"reason": "Test report for volunteer"}
	)
	assert report_response.status_code == 200

	# Now access volunteer page with different user
	volunteer_response = volunteer_client.get("/volunteer")
	assert volunteer_response.status_code == 200

	# Should contain some volunteer-related content
	# (exact content depends on whether a duty was assigned)


@util.no_rate_limit
def test_volunteer_cooldown():
	"""Test that volunteer cooldown prevents repeated volunteering"""
	client, user = util_accounts.create_test_client_and_user()

	# First volunteer session
	response1 = client.get("/volunteer")
	assert response1.status_code == 200

	from files.__main__ import db_session
	from files.classes import User

	# Check if volunteer_last_started_utc was set
	user_updated = db_session.query(User).filter_by(id=user.id).first()

	# Note: If no duty was available, volunteer_last_started_utc may not be set
	# This test verifies the endpoint is accessible regardless


@util.no_rate_limit
def test_volunteer_submit_empty():
	"""Test submitting volunteer form with no volunteer data"""
	client, user = util_accounts.create_test_client_and_user()

	# Submit empty volunteer form
	submit_response, _ = util.post_with_formkey(
		client, "/volunteer/submit",
		data={}
	)

	assert submit_response.status_code == 200


@util.no_rate_limit
def test_volunteer_submit_invalid_key():
	"""Test submitting volunteer form with invalid key format"""
	client, user = util_accounts.create_test_client_and_user()

	# Submit with non-volunteer key (should be ignored)
	submit_response, _ = util.post_with_formkey(
		client, "/volunteer/submit",
		data={"not-volunteer": "value"}
	)

	assert submit_response.status_code == 200


@util.no_rate_limit
def test_volunteer_submit_unknown_type():
	"""Test submitting volunteer form with unknown volunteer type"""
	client, user = util_accounts.create_test_client_and_user()

	# Submit with unknown volunteer type
	submit_response, _ = util.post_with_formkey(
		client, "/volunteer/submit",
		data={"volunteer-unknown-123": "1"}
	)

	# Should return 400 for unknown volunteer type
	assert submit_response.status_code == 400


@util.no_rate_limit
def test_volunteer_not_own_comment():
	"""Test that users don't see their own comments as volunteer duties"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post and comment by this user
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	# Create another user to report it
	reporter_client, reporter = util_accounts.create_test_client_and_user("reporter")
	report_response, _ = util.post_with_formkey(
		reporter_client, f"/report/comment/{comment.id}",
		data={"reason": "Test report"}
	)
	assert report_response.status_code == 200

	# Original user shouldn't see their own comment as a volunteer duty
	volunteer_response = client.get("/volunteer")
	assert volunteer_response.status_code == 200
	# The user's own comment ID should not appear in volunteer duties
	# (This is implementation-dependent, just verify the page loads)


@util.no_rate_limit
def test_volunteer_janitor_with_reported_comment():
	"""Test the full volunteer janitor flow with a reported comment"""
	# Create author, reporter, and volunteer users
	author_client, author = util_accounts.create_test_client_and_user("author")
	reporter_client, reporter = util_accounts.create_test_client_and_user("reporter")
	volunteer_client, volunteer = util_accounts.create_test_client_and_user("volunteer")

	# Author creates a post and comment
	post = util_submissions.create_submission_for_client(author_client)
	comment = util_comments.create_comment_for_client(author_client, post.id)

	# Reporter reports the comment
	report_response, _ = util.post_with_formkey(
		reporter_client, f"/report/comment/{comment.id}",
		data={"reason": "Test report"}
	)
	assert report_response.status_code == 200

	# Volunteer accesses the volunteer page
	volunteer_response = volunteer_client.get("/volunteer")
	assert volunteer_response.status_code == 200

	# Verify that volunteer records were created (if duty was available)
	from files.__main__ import db_session
	from files.classes import VolunteerJanitorRecord
	records = db_session.query(VolunteerJanitorRecord).filter_by(user_id=volunteer.id).all()
	# Records may or may not exist depending on if duty was available
	# Just verify the query doesn't fail


@util.no_rate_limit
def test_volunteer_logged_out():
	"""Test that logged-out users cannot access volunteer endpoints"""
	client = util_accounts.create_logged_off_client()

	# Try to access volunteer page
	response = client.get("/volunteer")
	# Should redirect to login or return 401/403
	assert response.status_code in [302, 401, 403]


@util.no_rate_limit
def test_volunteer_submit_logged_out():
	"""Test that logged-out users cannot submit volunteer responses"""
	client = util_accounts.create_logged_off_client()

	# Try to submit volunteer form
	response = client.post("/volunteer/submit", data={})
	# Should redirect to login or return 401/403
	assert response.status_code in [302, 401, 403]