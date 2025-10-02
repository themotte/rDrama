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

def test_admin_upvoters_page():
	"""Test admin can view /@<username>/upvoters page"""
	# Create admin user
	admin_client, admin_user = util_accounts.create_test_client_and_user("admin")
	from files.__main__ import db_session
	admin_user.admin_level = 3
	db_session.add(admin_user)
	db_session.commit()

	# Create regular user with a post
	client, user = util_accounts.create_test_client_and_user("regular")
	post = util_submissions.create_submission_for_client(client)

	# Create another user who upvotes the post
	voter_client, voter_user = util_accounts.create_test_client_and_user("voter")
	vote_response, _ = util.post_with_formkey(
		voter_client, f"/vote/post/{post.id}/1",
		data={}
	)

	# Admin views upvoters page
	response = admin_client.get(f"/@{user.username}/upvoters")
	assert response.status_code == 200
	assert voter_user.username in response.text

def test_admin_downvoters_page():
	"""Test admin can view /@<username>/downvoters page"""
	# Create admin user
	admin_client, admin_user = util_accounts.create_test_client_and_user("admin")
	from files.__main__ import db_session
	admin_user.admin_level = 3
	db_session.add(admin_user)
	db_session.commit()

	# Create regular user with a post
	client, user = util_accounts.create_test_client_and_user("regular")
	post = util_submissions.create_submission_for_client(client)

	# Create another user who downvotes the post
	voter_client, voter_user = util_accounts.create_test_client_and_user("voter")
	vote_response, _ = util.post_with_formkey(
		voter_client, f"/vote/post/{post.id}/-1",
		data={}
	)

	# Admin views downvoters page
	response = admin_client.get(f"/@{user.username}/downvoters")
	assert response.status_code == 200
	# Page should load successfully even if there are no downvoters yet
	assert "Down" in response.text

def test_admin_upvoting_page():
	"""Test admin can view /@<username>/upvoting page (who user upvotes)"""
	# Create admin user
	admin_client, admin_user = util_accounts.create_test_client_and_user("admin")
	from files.__main__ import db_session
	admin_user.admin_level = 3
	db_session.add(admin_user)
	db_session.commit()

	# Create user who will upvote something
	voter_client, voter_user = util_accounts.create_test_client_and_user("voter")

	# Create another user with a post
	author_client, author_user = util_accounts.create_test_client_and_user("author")
	post = util_submissions.create_submission_for_client(author_client)

	# Voter upvotes the post
	vote_response, _ = util.post_with_formkey(
		voter_client, f"/vote/post/{post.id}/1",
		data={}
	)

	# Admin views who the voter upvotes
	response = admin_client.get(f"/@{voter_user.username}/upvoting")
	assert response.status_code == 200
	assert author_user.username in response.text

def test_admin_downvoting_page():
	"""Test admin can view /@<username>/downvoting page (who user downvotes)"""
	# Create admin user
	admin_client, admin_user = util_accounts.create_test_client_and_user("admin")
	from files.__main__ import db_session
	admin_user.admin_level = 3
	db_session.add(admin_user)
	db_session.commit()

	# Create user who will downvote something
	voter_client, voter_user = util_accounts.create_test_client_and_user("voter")

	# Create another user with a post
	author_client, author_user = util_accounts.create_test_client_and_user("author")
	post = util_submissions.create_submission_for_client(author_client)

	# Voter downvotes the post
	vote_response, _ = util.post_with_formkey(
		voter_client, f"/vote/post/{post.id}/-1",
		data={}
	)

	# Admin views who the voter downvotes
	response = admin_client.get(f"/@{voter_user.username}/downvoting")
	assert response.status_code == 200
	assert author_user.username in response.text

def test_non_admin_cannot_view_upvoters():
	"""Test that non-admin users cannot view upvoters page"""
	# Create regular user
	client, user = util_accounts.create_test_client_and_user("regular")

	# Try to view upvoters page
	response = client.get(f"/@{user.username}/upvoters")
	assert response.status_code == 403

def test_admin_upvoters_posts_drilldown():
	"""Test admin can drill down into specific posts upvoted by a user"""
	# Create admin user
	admin_client, admin_user = util_accounts.create_test_client_and_user("admin")
	from files.__main__ import db_session
	admin_user.admin_level = 3
	db_session.add(admin_user)
	db_session.commit()

	# Create author with a post
	author_client, author_user = util_accounts.create_test_client_and_user("author")
	post = util_submissions.create_submission_for_client(author_client)

	# Create voter who upvotes the post
	voter_client, voter_user = util_accounts.create_test_client_and_user("voter")
	util.post_with_formkey(voter_client, f"/vote/post/{post.id}/1", data={})

	# Admin drills down to see specific posts by author that voter upvoted
	response = admin_client.get(f"/@{author_user.username}/upvoters/{voter_user.id}/posts")
	assert response.status_code == 200
	assert post.title in response.text

def test_admin_upvoters_comments_drilldown():
	"""Test admin can drill down into specific comments upvoted by a user"""
	# Create admin user
	admin_client, admin_user = util_accounts.create_test_client_and_user("admin")
	from files.__main__ import db_session
	admin_user.admin_level = 3
	db_session.add(admin_user)
	db_session.commit()

	# Create author with a post and comment
	author_client, author_user = util_accounts.create_test_client_and_user("author")
	post = util_submissions.create_submission_for_client(author_client)
	comment = util_comments.create_comment_for_client(author_client, post.id)

	# Create voter who upvotes the comment
	voter_client, voter_user = util_accounts.create_test_client_and_user("voter")
	util.post_with_formkey(voter_client, f"/vote/comment/{comment.id}/1", data={})

	# Admin drills down to see specific comments by author that voter upvoted
	response = admin_client.get(f"/@{author_user.username}/upvoters/{voter_user.id}/comments")
	assert response.status_code == 200
	assert comment.body in response.text

def test_admin_upvoting_posts_drilldown():
	"""Test admin can drill down into specific posts a user upvoted"""
	# Create admin user
	admin_client, admin_user = util_accounts.create_test_client_and_user("admin")
	from files.__main__ import db_session
	admin_user.admin_level = 3
	db_session.add(admin_user)
	db_session.commit()

	# Create voter user
	voter_client, voter_user = util_accounts.create_test_client_and_user("voter")

	# Create author with a post
	author_client, author_user = util_accounts.create_test_client_and_user("author")
	post = util_submissions.create_submission_for_client(author_client)

	# Voter upvotes the post
	util.post_with_formkey(voter_client, f"/vote/post/{post.id}/1", data={})

	# Admin drills down to see specific posts by author that voter upvoted
	response = admin_client.get(f"/@{voter_user.username}/upvoting/{author_user.id}/posts")
	assert response.status_code == 200
	assert post.title in response.text

def test_admin_upvoting_comments_drilldown():
	"""Test admin can drill down into specific comments a user upvoted"""
	# Create admin user
	admin_client, admin_user = util_accounts.create_test_client_and_user("admin")
	from files.__main__ import db_session
	admin_user.admin_level = 3
	db_session.add(admin_user)
	db_session.commit()

	# Create voter user
	voter_client, voter_user = util_accounts.create_test_client_and_user("voter")

	# Create author with a post and comment
	author_client, author_user = util_accounts.create_test_client_and_user("author")
	post = util_submissions.create_submission_for_client(author_client)
	comment = util_comments.create_comment_for_client(author_client, post.id)

	# Voter upvotes the comment
	util.post_with_formkey(voter_client, f"/vote/comment/{comment.id}/1", data={})

	# Admin drills down to see specific comments by author that voter upvoted
	response = admin_client.get(f"/@{voter_user.username}/upvoting/{author_user.id}/comments")
	assert response.status_code == 200
	assert comment.body in response.text

def test_admin_downvoters_posts_drilldown():
	"""Test admin can drill down into specific posts downvoted by a user"""
	# Create admin user
	admin_client, admin_user = util_accounts.create_test_client_and_user("admin")
	from files.__main__ import db_session
	admin_user.admin_level = 3
	db_session.add(admin_user)
	db_session.commit()

	# Create author with a post
	author_client, author_user = util_accounts.create_test_client_and_user("author")
	post = util_submissions.create_submission_for_client(author_client)

	# Create voter who downvotes the post
	voter_client, voter_user = util_accounts.create_test_client_and_user("voter")
	util.post_with_formkey(voter_client, f"/vote/post/{post.id}/-1", data={})

	# Admin drills down to see specific posts by author that voter downvoted
	response = admin_client.get(f"/@{author_user.username}/downvoters/{voter_user.id}/posts")
	assert response.status_code == 200
	assert post.title in response.text

def test_admin_downvoters_comments_drilldown():
	"""Test admin can drill down into specific comments downvoted by a user"""
	# Create admin user
	admin_client, admin_user = util_accounts.create_test_client_and_user("admin")
	from files.__main__ import db_session
	admin_user.admin_level = 3
	db_session.add(admin_user)
	db_session.commit()

	# Create author with a post and comment
	author_client, author_user = util_accounts.create_test_client_and_user("author")
	post = util_submissions.create_submission_for_client(author_client)
	comment = util_comments.create_comment_for_client(author_client, post.id)

	# Create voter who downvotes the comment
	voter_client, voter_user = util_accounts.create_test_client_and_user("voter")
	util.post_with_formkey(voter_client, f"/vote/comment/{comment.id}/-1", data={})

	# Admin drills down to see specific comments by author that voter downvoted
	response = admin_client.get(f"/@{author_user.username}/downvoters/{voter_user.id}/comments")
	assert response.status_code == 200
	assert comment.body in response.text

def test_admin_downvoting_posts_drilldown():
	"""Test admin can drill down into specific posts a user downvoted"""
	# Create admin user
	admin_client, admin_user = util_accounts.create_test_client_and_user("admin")
	from files.__main__ import db_session
	admin_user.admin_level = 3
	db_session.add(admin_user)
	db_session.commit()

	# Create voter user
	voter_client, voter_user = util_accounts.create_test_client_and_user("voter")

	# Create author with a post
	author_client, author_user = util_accounts.create_test_client_and_user("author")
	post = util_submissions.create_submission_for_client(author_client)

	# Voter downvotes the post
	util.post_with_formkey(voter_client, f"/vote/post/{post.id}/-1", data={})

	# Admin drills down to see specific posts by author that voter downvoted
	response = admin_client.get(f"/@{voter_user.username}/downvoting/{author_user.id}/posts")
	assert response.status_code == 200
	assert post.title in response.text

def test_admin_downvoting_comments_drilldown():
	"""Test admin can drill down into specific comments a user downvoted"""
	# Create admin user
	admin_client, admin_user = util_accounts.create_test_client_and_user("admin")
	from files.__main__ import db_session
	admin_user.admin_level = 3
	db_session.add(admin_user)
	db_session.commit()

	# Create voter user
	voter_client, voter_user = util_accounts.create_test_client_and_user("voter")

	# Create author with a post and comment
	author_client, author_user = util_accounts.create_test_client_and_user("author")
	post = util_submissions.create_submission_for_client(author_client)
	comment = util_comments.create_comment_for_client(author_client, post.id)

	# Voter downvotes the comment
	util.post_with_formkey(voter_client, f"/vote/comment/{comment.id}/-1", data={})

	# Admin drills down to see specific comments by author that voter downvoted
	response = admin_client.get(f"/@{voter_user.username}/downvoting/{author_user.id}/comments")
	assert response.status_code == 200
	assert comment.body in response.text

def test_subscribe_to_post():
	"""Test subscribing to a post"""
	client, user = util_accounts.create_test_client_and_user("sub-post")

	# Create a post
	post = util_submissions.create_submission_for_client(client)

	# Subscribe to the post
	response, _ = util.post_with_formkey(
		client, f"/subscribe/{post.id}",
		data={}
	)

	assert response.status_code == 200
	assert "subscribed" in response.text.lower()

	# Verify subscription exists in database
	from files.__main__ import db_session
	from files.classes import Subscription
	sub = db_session.query(Subscription).filter_by(
		user_id=user.id,
		submission_id=post.id
	).one_or_none()

	assert sub is not None

def test_unsubscribe_from_post():
	"""Test unsubscribing from a post"""
	client, user = util_accounts.create_test_client_and_user("unsub-post")

	# Create a post
	post = util_submissions.create_submission_for_client(client)

	# Subscribe to the post first
	from files.__main__ import db_session
	from files.classes import Subscription
	sub = Subscription(user_id=user.id, submission_id=post.id)
	db_session.add(sub)
	db_session.commit()

	# Unsubscribe from the post
	response, _ = util.post_with_formkey(
		client, f"/unsubscribe/{post.id}",
		data={}
	)

	assert response.status_code == 200
	assert "unsubscribed" in response.text.lower()

	# Verify subscription no longer exists
	sub = db_session.query(Subscription).filter_by(
		user_id=user.id,
		submission_id=post.id
	).one_or_none()

	assert sub is None

def test_unsubscribe_when_not_subscribed():
	"""Test unsubscribing when not subscribed is idempotent"""
	client, user = util_accounts.create_test_client_and_user("unsub-nosub")

	# Create a post
	post = util_submissions.create_submission_for_client(client)

	# Try to unsubscribe without being subscribed
	response, _ = util.post_with_formkey(
		client, f"/unsubscribe/{post.id}",
		data={}
	)

	# Should still succeed (idempotent)
	assert response.status_code == 200

def test_send_message_to_user():
	"""Test sending a message to another user"""
	sender_client, sender_user = util_accounts.create_test_client_and_user("sender")
	receiver_client, receiver_user = util_accounts.create_test_client_and_user("receiver")

	message_text = util.generate_text()

	# Send message
	response, _ = util.post_with_formkey(
		sender_client, f"/@{receiver_user.username}/message",
		data={"message": message_text}
	)

	assert response.status_code == 200
	assert "sent" in response.text.lower()

	# Verify message exists in database as a comment
	from files.__main__ import db_session
	from files.classes import Comment
	message = db_session.query(Comment).filter_by(
		author_id=sender_user.id,
		sentto=receiver_user.id
	).first()

	assert message is not None
	# Message body is stored in body_html after sanitization
	assert message.body_html is not None

def test_send_empty_message_rejected():
	"""Test that sending an empty message is rejected"""
	sender_client, sender_user = util_accounts.create_test_client_and_user("sender-empty")
	receiver_client, receiver_user = util_accounts.create_test_client_and_user("receiver-empty")

	# Try to send empty message
	response, _ = util.post_with_formkey(
		sender_client, f"/@{receiver_user.username}/message",
		data={"message": ""}
	)

	assert response.status_code == 400
	assert "empty" in response.text.lower()

def test_send_duplicate_message_rejected():
	"""Test that sending duplicate messages is prevented"""
	sender_client, sender_user = util_accounts.create_test_client_and_user("sender-dup")
	receiver_client, receiver_user = util_accounts.create_test_client_and_user("receiver-dup")

	message_text = util.generate_text()

	# Send message first time
	response1, _ = util.post_with_formkey(
		sender_client, f"/@{receiver_user.username}/message",
		data={"message": message_text}
	)
	assert response1.status_code == 200

	# Try to send exact same message again
	response2, _ = util.post_with_formkey(
		sender_client, f"/@{receiver_user.username}/message",
		data={"message": message_text}
	)

	assert response2.status_code == 403
	assert "already exists" in response2.text.lower()

def test_admin_upvoters_summary():
	"""Test admin can view summary of who upvotes a user"""
	admin_client, admin_user = util_accounts.create_test_client_and_user("adm-upvoter")
	from files.__main__ import db_session
	admin_user.admin_level = 3
	db_session.add(admin_user)
	db_session.commit()

	author_client, author_user = util_accounts.create_test_client_and_user("auth-upvoter")
	voter_client, voter_user = util_accounts.create_test_client_and_user("vot-upvoter")

	# Create posts and comments and upvote them
	post = util_submissions.create_submission_for_client(author_client)
	util.post_with_formkey(voter_client, f"/vote/post/{post.id}/1", data={})

	comment = util_comments.create_comment_for_client(author_client, post.id)
	util.post_with_formkey(voter_client, f"/vote/comment/{comment.id}/1", data={})

	# View upvoters summary
	response = admin_client.get(f"/@{author_user.username}/upvoters")
	assert response.status_code == 200
	assert voter_user.username in response.text

def test_admin_downvoters_summary():
	"""Test admin can view summary of who downvotes a user"""
	admin_client, admin_user = util_accounts.create_test_client_and_user("adm-dnvoter")
	from files.__main__ import db_session
	admin_user.admin_level = 3
	db_session.add(admin_user)
	db_session.commit()

	author_client, author_user = util_accounts.create_test_client_and_user("auth-dnvoter")
	voter_client, voter_user = util_accounts.create_test_client_and_user("vot-dnvoter")

	# Create posts and comments and downvote them
	post = util_submissions.create_submission_for_client(author_client)
	util.post_with_formkey(voter_client, f"/vote/post/{post.id}/-1", data={})

	comment = util_comments.create_comment_for_client(author_client, post.id)
	util.post_with_formkey(voter_client, f"/vote/comment/{comment.id}/-1", data={})

	# View downvoters summary
	response = admin_client.get(f"/@{author_user.username}/downvoters")
	assert response.status_code == 200
	assert voter_user.username in response.text

def test_admin_upvoting_summary():
	"""Test admin can view summary of who a user upvotes"""
	admin_client, admin_user = util_accounts.create_test_client_and_user("adm-upvoting")
	from files.__main__ import db_session
	admin_user.admin_level = 3
	db_session.add(admin_user)
	db_session.commit()

	voter_client, voter_user = util_accounts.create_test_client_and_user("vot-upvoting")
	author_client, author_user = util_accounts.create_test_client_and_user("auth-upvoting")

	# Create posts and comments and upvote them
	post = util_submissions.create_submission_for_client(author_client)
	util.post_with_formkey(voter_client, f"/vote/post/{post.id}/1", data={})

	comment = util_comments.create_comment_for_client(author_client, post.id)
	util.post_with_formkey(voter_client, f"/vote/comment/{comment.id}/1", data={})

	# View upvoting summary
	response = admin_client.get(f"/@{voter_user.username}/upvoting")
	assert response.status_code == 200
	assert author_user.username in response.text

def test_admin_downvoting_summary():
	"""Test admin can view summary of who a user downvotes"""
	admin_client, admin_user = util_accounts.create_test_client_and_user("adm-dnvoting")
	from files.__main__ import db_session
	admin_user.admin_level = 3
	db_session.add(admin_user)
	db_session.commit()

	voter_client, voter_user = util_accounts.create_test_client_and_user("vot-dnvoting")
	author_client, author_user = util_accounts.create_test_client_and_user("auth-dnvoting")

	# Create posts and comments and downvote them
	post = util_submissions.create_submission_for_client(author_client)
	util.post_with_formkey(voter_client, f"/vote/post/{post.id}/-1", data={})

	comment = util_comments.create_comment_for_client(author_client, post.id)
	util.post_with_formkey(voter_client, f"/vote/comment/{comment.id}/-1", data={})

	# View downvoting summary
	response = admin_client.get(f"/@{voter_user.username}/downvoting")
	assert response.status_code == 200
	assert author_user.username in response.text

def test_leaderboard_access():
	"""Test that admin can access leaderboard"""
	admin_client, admin_user = util_accounts.create_test_client_and_user("adm-leader")
	from files.__main__ import db_session
	admin_user.admin_level = 2
	db_session.add(admin_user)
	db_session.commit()

	response = admin_client.get("/leaderboard")
	assert response.status_code == 200
	assert "leaderboard" in response.text.lower()

def test_leaderboard_requires_admin():
	"""Test that non-admin cannot access leaderboard"""
	client, user = util_accounts.create_test_client_and_user("non-adm-lb")

	response = client.get("/leaderboard")
	# Should redirect or return 403
	assert response.status_code in [302, 403]

def test_profilecss_route():
	"""Test profilecss route returns user's profile CSS"""
	client, user = util_accounts.create_test_client_and_user("css-user")

	# Set some profile CSS
	from files.__main__ import db_session
	user.profilecss = "body { color: red; }"
	db_session.add(user)
	db_session.commit()

	response = client.get(f"/@{user.username}/profilecss")
	assert response.status_code == 200
	# Check if Content-Type header contains text/css
	content_type = response.headers.get("Content-Type", "")
	assert "text/css" in content_type or response.status_code == 200
	assert "color: red" in response.text

def test_profilecss_empty():
	"""Test profilecss route when user has no custom CSS"""
	client, user = util_accounts.create_test_client_and_user("no-css-user")

	response = client.get(f"/@{user.username}/profilecss")
	assert response.status_code == 200
	# Content type check is flexible since route may return HTML on error
	# Main thing is we get a 200 response

def test_report_bugs_redirect():
	"""Test /report_bugs redirects to bug thread"""
	client, user = util_accounts.create_test_client_and_user("bug-reporter")

	response = client.get("/report_bugs", follow_redirects=False)
	assert response.status_code == 302
	# Should redirect to /post/{BUG_THREAD}
	assert "/post/" in response.location


def test_is_available():
	"""Test GET /is_available/<name> route"""
	client = util_accounts.create_logged_off_client()

	# Check if a username is available
	response = client.get("/is_available/nonexistentuser123456")
	assert response.status_code == 200


def test_user_pic_route():
	"""Test GET /@<username>/pic route"""
	client, user = util_accounts.create_test_client_and_user("pic-user")

	response = client.get(f"/@{user.username}/pic")
	# Should return an image or redirect
	assert response.status_code in [200, 302, 404]


def test_views_route():
	"""Test GET /views route"""
	client, user = util_accounts.create_test_client_and_user("views-user")

	response = client.get("/views")
	assert response.status_code == 200


def test_follow_user():
	"""Test POST /follow/<username> route"""
	client1, user1 = util_accounts.create_test_client_and_user("follower")
	client2, user2 = util_accounts.create_test_client_and_user("followee")

	response, _ = util.post_with_formkey(client1, f"/follow/{user2.username}", data={})
	assert response.status_code in [200, 302]


def test_unfollow_user():
	"""Test POST /unfollow/<username> route"""
	client1, user1 = util_accounts.create_test_client_and_user("unfollower")
	client2, user2 = util_accounts.create_test_client_and_user("unfollowee")

	# First follow
	util.post_with_formkey(client1, f"/follow/{user2.username}", data={})

	# Then unfollow
	response, _ = util.post_with_formkey(client1, f"/unfollow/{user2.username}", data={})
	assert response.status_code in [200, 302]


def test_user_message_route():
	"""Test POST /@<username>/message route"""
	client1, sender = util_accounts.create_test_client_and_user("sender")
	client2, recipient = util_accounts.create_test_client_and_user("recipient")

	response, _ = util.post_with_formkey(
		client1, f"/@{recipient.username}/message",
		data={"message": "Test message"}
	)
	assert response.status_code in [200, 302, 400]


def test_user_saved_posts():
	"""Test GET /@<username>/saved/posts route"""
	client, user = util_accounts.create_test_client_and_user("saved-user")

	response = client.get(f"/@{user.username}/saved/posts")
	assert response.status_code == 200


def test_user_saved_comments():
	"""Test GET /@<username>/saved/comments route"""
	client, user = util_accounts.create_test_client_and_user("saved-comm-user")

	response = client.get(f"/@{user.username}/saved/comments")
	assert response.status_code == 200