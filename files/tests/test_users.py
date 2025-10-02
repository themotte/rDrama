from . import util_accounts
from . import util
from . import util_submissions
from . import util_comments

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

def test_profilecss_nonexistent_user():
	"""Test profilecss endpoint with nonexistent user"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/@nonexistentuser/profilecss")
	assert response.status_code == 404

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
		client, f"/subscribe/{post.id}",
		data={}
	)

	assert subscribe_response.status_code == 200
	assert "Post subscribed!" in subscribe_response.text

	# Verify subscription was created in database
	subs = db_session.query(Subscription).filter_by(user_id=user.id, submission_id=post.id).all()
	assert len(subs) == 1

	# Unsubscribe from the post
	unsubscribe_response, _ = util.post_with_formkey(
		client, f"/unsubscribe/{post.id}",
		data={}
	)

	assert unsubscribe_response.status_code == 200
	assert "Post unsubscribed!" in unsubscribe_response.text

	# Verify subscription was removed from database
	subs = db_session.query(Subscription).filter_by(user_id=user.id, submission_id=post.id).all()
	assert len(subs) == 0

def test_unsubscribe_nonexistent_subscription():
	"""Test unsubscribing from a post when no subscription exists"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post but don't subscribe to it
	post = util_submissions.create_submission_for_client(client)

	# Try to unsubscribe (should not fail)
	unsubscribe_response, _ = util.post_with_formkey(
		client, f"/unsubscribe/{post.id}",
		data={}
	)

	assert unsubscribe_response.status_code == 200
	assert "Post unsubscribed!" in unsubscribe_response.text

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

def test_user_info_nonexistent_user():
	"""Test user info endpoint with nonexistent user"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/@nonexistentuser/info")
	assert response.status_code == 404

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
		client, f"/follow/{user2.username}",
		data={}
	)

	assert follow_response.status_code == 200
	assert "User followed!" in follow_response.text

	# Verify follow relationship was created in database
	follows = db_session.query(Follow).filter_by(user_id=user1.id, target_id=user2.id).all()
	assert len(follows) == 1

def test_follow_self():
	"""Test that users cannot follow themselves"""
	client, user = util_accounts.create_test_client_and_user()

	# Try to follow self
	follow_response, _ = util.post_with_formkey(
		client, f"/follow/{user.username}",
		data={}
	)

	assert follow_response.status_code == 400

def test_follow_already_following():
	"""Test following a user you're already following"""
	client, user1 = util_accounts.create_test_client_and_user("user1")
	_, user2 = util_accounts.create_test_client_and_user("user2")

	# Follow user2 first time
	follow_response1, _ = util.post_with_formkey(
		client, f"/follow/{user2.username}",
		data={}
	)
	assert follow_response1.status_code == 200

	# Follow user2 second time (should still return success)
	follow_response2, _ = util.post_with_formkey(
		client, f"/follow/{user2.username}",
		data={}
	)
	assert follow_response2.status_code == 200
	assert "User followed!" in follow_response2.text

	# Verify only one follow relationship exists
	from files.__main__ import db_session
	from files.classes import Follow
	follows = db_session.query(Follow).filter_by(user_id=user1.id, target_id=user2.id).all()
	assert len(follows) == 1

def test_unfollow_user():
	"""Test unfollowing a user"""
	client, user1 = util_accounts.create_test_client_and_user("user1")
	_, user2 = util_accounts.create_test_client_and_user("user2")

	# Follow user2 first
	follow_response, _ = util.post_with_formkey(
		client, f"/follow/{user2.username}",
		data={}
	)
	assert follow_response.status_code == 200

	# Verify follow relationship exists
	from files.__main__ import db_session
	from files.classes import Follow
	follows = db_session.query(Follow).filter_by(user_id=user1.id, target_id=user2.id).all()
	assert len(follows) == 1

	# Unfollow user2
	unfollow_response, _ = util.post_with_formkey(
		client, f"/unfollow/{user2.username}",
		data={}
	)
	assert unfollow_response.status_code == 200
	assert "User unfollowed!" in unfollow_response.text

	# Verify follow relationship was removed
	follows = db_session.query(Follow).filter_by(user_id=user1.id, target_id=user2.id).all()
	assert len(follows) == 0

def test_unfollow_not_following():
	"""Test unfollowing a user you're not following"""
	client, user1 = util_accounts.create_test_client_and_user("user1")
	_, user2 = util_accounts.create_test_client_and_user("user2")

	# Try to unfollow without following first
	unfollow_response, _ = util.post_with_formkey(
		client, f"/unfollow/{user2.username}",
		data={}
	)

	# Should still return 200 (idempotent)
	assert unfollow_response.status_code == 200

def test_remove_follower():
	"""Test removing a follower"""
	client1, user1 = util_accounts.create_test_client_and_user("user1")
	client2, user2 = util_accounts.create_test_client_and_user("user2")

	# User2 follows user1
	follow_response, _ = util.post_with_formkey(
		client2, f"/follow/{user1.username}",
		data={}
	)
	assert follow_response.status_code == 200

	# Verify follow relationship exists
	from files.__main__ import db_session
	from files.classes import Follow
	follows = db_session.query(Follow).filter_by(user_id=user2.id, target_id=user1.id).all()
	assert len(follows) == 1

	# User1 removes user2 as a follower
	remove_response, _ = util.post_with_formkey(
		client1, f"/remove_follow/{user2.username}",
		data={}
	)
	assert remove_response.status_code == 200
	assert "Follower removed!" in remove_response.text

	# Verify follow relationship was removed
	follows = db_session.query(Follow).filter_by(user_id=user2.id, target_id=user1.id).all()
	assert len(follows) == 0

def test_is_available_valid_name():
	"""Test username availability check for an available name"""
	client = util_accounts.create_logged_off_client()

	# Check an available name
	response = client.get("/is_available/newusername123")
	assert response.status_code == 200

	import json
	data = json.loads(response.text)
	assert data["newusername123"] == True

def test_is_available_taken_name():
	"""Test username availability check for a taken name"""
	client, user = util_accounts.create_test_client_and_user("testuser")

	# Check the taken username
	response = client.get(f"/is_available/{user.username}")
	assert response.status_code == 200

	import json
	data = json.loads(response.text)
	assert data[user.username] == False

def test_is_available_too_short():
	"""Test username availability check for a name that's too short"""
	client = util_accounts.create_logged_off_client()

	# Check a name that's too short (less than 3 chars)
	response = client.get("/is_available/ab")
	assert response.status_code == 200

	import json
	data = json.loads(response.text)
	assert data["ab"] == False

def test_is_available_too_long():
	"""Test username availability check for a name that's too long"""
	client = util_accounts.create_logged_off_client()

	# Check a name that's too long (more than 25 chars)
	long_name = "a" * 26
	response = client.get(f"/is_available/{long_name}")
	assert response.status_code == 200

	import json
	data = json.loads(response.text)
	assert data[long_name] == False

def test_user_id_redirect():
	"""Test /id/<int:id> redirects to user profile"""
	client, user = util_accounts.create_test_client_and_user()

	# Test redirect to user profile
	response = client.get(f"/id/{user.id}", follow_redirects=False)
	assert response.status_code == 302
	assert f"/@{user.username}" in response.location

def test_redditor_redirect():
	"""Test /u/<username> redirects to /@<username>"""
	client, user = util_accounts.create_test_client_and_user()

	# Test Reddit-style redirect
	response = client.get(f"/u/{user.username}", follow_redirects=False)
	assert response.status_code == 302
	assert f"/@{user.username}" in response.location

def test_followers_list():
	"""Test /@<username>/followers endpoint"""
	client1, user1 = util_accounts.create_test_client_and_user("user1")
	client2, user2 = util_accounts.create_test_client_and_user("user2")

	# User2 follows user1
	follow_response, _ = util.post_with_formkey(
		client2, f"/follow/{user1.username}",
		data={}
	)
	assert follow_response.status_code == 200

	# Check user1's followers list
	response = client1.get(f"/@{user1.username}/followers")
	assert response.status_code == 200
	assert user2.username in response.text

def test_following_list():
	"""Test /@<username>/following endpoint"""
	client1, user1 = util_accounts.create_test_client_and_user("user1")
	_, user2 = util_accounts.create_test_client_and_user("user2")

	# User1 follows user2
	follow_response, _ = util.post_with_formkey(
		client1, f"/follow/{user2.username}",
		data={}
	)
	assert follow_response.status_code == 200

	# Check user1's following list
	response = client1.get(f"/@{user1.username}/following")
	assert response.status_code == 200
	assert user2.username in response.text

def test_saved_posts_view():
	"""Test viewing saved posts"""
	client, user = util_accounts.create_test_client_and_user()

	# Create and save a post
	post = util_submissions.create_submission_for_client(client)

	# Save the post
	from files.__main__ import db_session
	from files.classes import SaveRelationship
	save = SaveRelationship(user_id=user.id, submission_id=post.id)
	db_session.add(save)
	db_session.commit()

	# View saved posts
	response = client.get(f"/@{user.username}/saved/posts")
	assert response.status_code == 200
	assert post.title in response.text

def test_saved_comments_view():
	"""Test viewing saved comments"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post and comment
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	# Save the comment
	from files.__main__ import db_session
	from files.classes import CommentSaveRelationship
	save = CommentSaveRelationship(user_id=user.id, comment_id=comment.id)
	db_session.add(save)
	db_session.commit()

	# View saved comments
	response = client.get(f"/@{user.username}/saved/comments")
	assert response.status_code == 200
	assert comment.body in response.text

def test_user_posts_page():
	"""Test /@<username>/posts endpoint"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post
	post = util_submissions.create_submission_for_client(client)

	# View user's posts page
	response = client.get(f"/@{user.username}/posts")
	assert response.status_code == 200
	assert post.title in response.text

def test_user_comments_page():
	"""Test /@<username>/ endpoint (comments page)"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post and comment
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	# View user's comments page
	response = client.get(f"/@{user.username}/")
	assert response.status_code == 200
	assert comment.body in response.text

def test_user_posts_page_pagination():
	"""Test /@<username>/posts pagination"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post
	post = util_submissions.create_submission_for_client(client)

	# View user's posts page with pagination
	response = client.get(f"/@{user.username}/posts?page=1")
	assert response.status_code == 200
	assert post.title in response.text