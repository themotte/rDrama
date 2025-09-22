from . import util_accounts
from . import util
from . import util_submissions

@util.no_rate_limit
def test_profilecss_endpoint():
	"""Test the /@<username>/profilecss endpoint"""
	client, user = util_accounts.create_test_client_and_user()

	# Test user with no profilecss
	response = client.get(f"/@{user.username}/profilecss")
	assert response.status_code == 200
	# Note: Content-Type may not be set to text/css in test environment
	assert response.text == ""

	# Set some profilecss for the user
	from files.__main__ import db_session
	user.profilecss = "body { background-color: red; }"
	db_session.add(user)
	db_session.commit()

	# Test user with profilecss
	response = client.get(f"/@{user.username}/profilecss")
	assert response.status_code == 200
	assert response.text == "body { background-color: red; }"

@util.no_rate_limit
def test_profilecss_nonexistent_user():
	"""Test profilecss endpoint with nonexistent user"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/@nonexistentuser/profilecss")
	assert response.status_code == 404

@util.no_rate_limit
def test_subscribe_unsubscribe_post():
	"""Test subscribing and unsubscribing to posts"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post to subscribe to
	post = util_submissions.create_submission_for_client(client)

	# Check that no subscription exists initially
	from files.__main__ import db_session
	from files.classes import Subscription
	initial_subs = db_session.query(Subscription).filter_by(user_id=user.id, submission_id=post.id).count()
	assert initial_subs == 0

	# Subscribe to the post
	subscribe_response, _ = util.post_with_formkey(
		client, "/submit", f"/subscribe/{post.id}",
		data={}
	)

	assert subscribe_response.status_code == 200
	assert "Post subscribed!" in subscribe_response.text

	# Verify subscription was created in database
	subs = db_session.query(Subscription).filter_by(user_id=user.id, submission_id=post.id).all()
	assert len(subs) == 1

	# Unsubscribe from the post
	unsubscribe_response, _ = util.post_with_formkey(
		client, "/submit", f"/unsubscribe/{post.id}",
		data={}
	)

	assert unsubscribe_response.status_code == 200
	assert "Post unsubscribed!" in unsubscribe_response.text

	# Verify subscription was removed from database
	subs = db_session.query(Subscription).filter_by(user_id=user.id, submission_id=post.id).all()
	assert len(subs) == 0

@util.no_rate_limit
def test_unsubscribe_nonexistent_subscription():
	"""Test unsubscribing from a post when no subscription exists"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post but don't subscribe to it
	post = util_submissions.create_submission_for_client(client)

	# Try to unsubscribe (should not fail)
	unsubscribe_response, _ = util.post_with_formkey(
		client, "/submit", f"/unsubscribe/{post.id}",
		data={}
	)

	assert unsubscribe_response.status_code == 200
	assert "Post unsubscribed!" in unsubscribe_response.text

@util.no_rate_limit
def test_user_info_endpoint():
	"""Test the /@<username>/info endpoint"""
	client, user = util_accounts.create_test_client_and_user()

	# Test getting user info
	response = client.get(f"/@{user.username}/info")
	assert response.status_code == 200

	# Check that it returns JSON
	import json
	user_info = json.loads(response.text)
	assert isinstance(user_info, dict)
	assert "username" in user_info
	assert user_info["username"] == user.username
	assert "id" in user_info
	assert user_info["id"] == user.id

@util.no_rate_limit
def test_user_info_nonexistent_user():
	"""Test user info endpoint with nonexistent user"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/@nonexistentuser/info")
	assert response.status_code == 404

@util.no_rate_limit
def test_follow_user():
	"""Test following another user"""
	client, user1 = util_accounts.create_test_client_and_user("user1")
	_, user2 = util_accounts.create_test_client_and_user("user2")

	# Check that no follow relationship exists initially
	from files.__main__ import db_session
	from files.classes import Follow
	initial_follows = db_session.query(Follow).filter_by(user_id=user1.id, target_id=user2.id).count()
	assert initial_follows == 0

	# Follow user2
	follow_response, _ = util.post_with_formkey(
		client, "/submit", f"/follow/{user2.username}",
		data={}
	)

	assert follow_response.status_code == 200
	assert "User followed!" in follow_response.text

	# Verify follow relationship was created in database
	follows = db_session.query(Follow).filter_by(user_id=user1.id, target_id=user2.id).all()
	assert len(follows) == 1

@util.no_rate_limit
def test_follow_self():
	"""Test that users cannot follow themselves"""
	client, user = util_accounts.create_test_client_and_user()

	# Try to follow self
	follow_response, _ = util.post_with_formkey(
		client, "/submit", f"/follow/{user.username}",
		data={}
	)

	assert follow_response.status_code == 400

@util.no_rate_limit
def test_follow_already_following():
	"""Test following a user you're already following"""
	client, user1 = util_accounts.create_test_client_and_user("user1")
	_, user2 = util_accounts.create_test_client_and_user("user2")

	# Follow user2 first time
	follow_response1, _ = util.post_with_formkey(
		client, "/submit", f"/follow/{user2.username}",
		data={}
	)
	assert follow_response1.status_code == 200

	# Follow user2 second time (should still return success)
	follow_response2, _ = util.post_with_formkey(
		client, "/submit", f"/follow/{user2.username}",
		data={}
	)
	assert follow_response2.status_code == 200
	assert "User followed!" in follow_response2.text

	# Verify only one follow relationship exists
	from files.__main__ import db_session
	from files.classes import Follow
	follows = db_session.query(Follow).filter_by(user_id=user1.id, target_id=user2.id).all()
	assert len(follows) == 1