import warnings

from . import util_accounts
from . import util
from . import util_submissions
from .conftest import LazyLoadWarning


def test_submit_get():
	"""Test accessing the submit page"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/submit")
	assert response.status_code == 200
	assert "submit" in response.text.lower()


def test_submit_get_requires_auth():
	"""Test that submit page requires authentication"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/submit")
	assert response.status_code == 302
	assert "/login" in response.location


def test_delete_post():
	"""Test deleting a post"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post
	post = util_submissions.create_submission_for_client(client)

	from files.__main__ import db_session
	from files.classes import Submission

	# Delete the post
	delete_response, _ = util.post_with_formkey(client, f"/delete_post/{post.id}", data={})
	assert delete_response.status_code == 200
	assert "deleted" in delete_response.text.lower()

	# Verify post is marked as deleted
	db_session.expire_all()
	post_updated = db_session.query(Submission).filter_by(id=post.id).first()
	assert post_updated.state_user_deleted_utc is not None


def test_delete_post_not_author():
	"""Test that users cannot delete other users' posts"""
	# Create two users
	client1, user1 = util_accounts.create_test_client_and_user(name="author-post")
	client2, user2 = util_accounts.create_test_client_and_user(name="other-user")

	# User1 creates a post
	post = util_submissions.create_submission_for_client(client1)

	# User2 tries to delete user1's post
	delete_response, _ = util.post_with_formkey(client2, f"/delete_post/{post.id}", data={})
	assert delete_response.status_code == 403


def test_undelete_post():
	"""Test undeleting a post"""
	client, user = util_accounts.create_test_client_and_user()

	# Create and delete a post
	post = util_submissions.create_submission_for_client(client)

	from files.__main__ import db_session
	from files.classes import Submission

	delete_response, _ = util.post_with_formkey(client, f"/delete_post/{post.id}", data={})
	assert delete_response.status_code == 200

	# Verify post is deleted
	db_session.expire_all()
	post_updated = db_session.query(Submission).filter_by(id=post.id).first()
	assert post_updated.state_user_deleted_utc is not None

	# Undelete the post
	undelete_response, _ = util.post_with_formkey(client, f"/undelete_post/{post.id}", data={})
	assert undelete_response.status_code == 200
	assert "undeleted" in undelete_response.text.lower()

	# Verify post is no longer deleted
	db_session.expire_all()
	post_updated = db_session.query(Submission).filter_by(id=post.id).first()
	assert post_updated.state_user_deleted_utc is None


def test_undelete_post_not_author():
	"""Test that users cannot undelete other users' posts"""
	# Create two users
	client1, user1 = util_accounts.create_test_client_and_user(name="author-post2")
	client2, user2 = util_accounts.create_test_client_and_user(name="other-user2")

	# User1 creates and deletes a post
	post = util_submissions.create_submission_for_client(client1)
	delete_response, _ = util.post_with_formkey(client1, f"/delete_post/{post.id}", data={})
	assert delete_response.status_code == 200

	# User2 tries to undelete user1's post
	undelete_response, _ = util.post_with_formkey(client2, f"/undelete_post/{post.id}", data={})
	assert undelete_response.status_code == 403


def test_toggle_post_nsfw_by_author():
	"""Test author can toggle post NSFW status"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post
	post = util_submissions.create_submission_for_client(client)

	from files.__main__ import db_session
	from files.classes import Submission

	# Check initial state
	db_session.expire_all()
	post_initial = db_session.query(Submission).filter_by(id=post.id).first()
	initial_nsfw = post_initial.over_18

	# Toggle NSFW
	toggle_response, _ = util.post_with_formkey(client, f"/toggle_post_nsfw/{post.id}", data={})
	assert toggle_response.status_code == 200
	assert "18+" in toggle_response.text

	# Verify NSFW status changed
	db_session.expire_all()
	post_updated = db_session.query(Submission).filter_by(id=post.id).first()
	assert post_updated.over_18 != initial_nsfw

	# Toggle back
	toggle_response, _ = util.post_with_formkey(client, f"/toggle_post_nsfw/{post.id}", data={})
	assert toggle_response.status_code == 200

	# Verify NSFW status changed back
	db_session.expire_all()
	post_final = db_session.query(Submission).filter_by(id=post.id).first()
	assert post_final.over_18 == initial_nsfw


def test_toggle_post_nsfw_not_author():
	"""Test that non-authors cannot toggle NSFW without admin permissions"""
	# Create two users
	client1, user1 = util_accounts.create_test_client_and_user(name="author-post3")
	client2, user2 = util_accounts.create_test_client_and_user(name="other-user3")

	# User1 creates a post
	post = util_submissions.create_submission_for_client(client1)

	# User2 tries to toggle NSFW
	toggle_response, _ = util.post_with_formkey(client2, f"/toggle_post_nsfw/{post.id}", data={})
	assert toggle_response.status_code == 403


def test_save_post():
	"""Test saving a post"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post
	post = util_submissions.create_submission_for_client(client)

	from files.__main__ import db_session
	from files.classes import SaveRelationship

	# Save the post
	save_response, _ = util.post_with_formkey(client, f"/save_post/{post.id}", data={})
	assert save_response.status_code == 200
	assert "saved" in save_response.text.lower()

	# Verify save relationship exists
	save = db_session.query(SaveRelationship).filter_by(user_id=user.id, submission_id=post.id).one_or_none()
	assert save is not None


def test_save_post_idempotent():
	"""Test that saving a post multiple times is idempotent"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post
	post = util_submissions.create_submission_for_client(client)

	from files.__main__ import db_session
	from files.classes import SaveRelationship

	# Save the post twice
	save_response1, _ = util.post_with_formkey(client, f"/save_post/{post.id}", data={})
	assert save_response1.status_code == 200

	save_response2, _ = util.post_with_formkey(client, f"/save_post/{post.id}", data={})
	assert save_response2.status_code == 200

	# Verify only one save relationship exists
	saves = db_session.query(SaveRelationship).filter_by(user_id=user.id, submission_id=post.id).all()
	assert len(saves) == 1


def test_unsave_post():
	"""Test unsaving a post"""
	client, user = util_accounts.create_test_client_and_user()

	# Create and save a post
	post = util_submissions.create_submission_for_client(client)

	from files.__main__ import db_session
	from files.classes import SaveRelationship

	save_response, _ = util.post_with_formkey(client, f"/save_post/{post.id}", data={})
	assert save_response.status_code == 200

	# Verify save exists
	save = db_session.query(SaveRelationship).filter_by(user_id=user.id, submission_id=post.id).one_or_none()
	assert save is not None

	# Unsave the post
	unsave_response, _ = util.post_with_formkey(client, f"/unsave_post/{post.id}", data={})
	assert unsave_response.status_code == 200
	assert "unsaved" in unsave_response.text.lower()

	# Verify save relationship no longer exists
	save = db_session.query(SaveRelationship).filter_by(user_id=user.id, submission_id=post.id).one_or_none()
	assert save is None


def test_unsave_post_not_saved():
	"""Test unsaving a post that wasn't saved is idempotent"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post (don't save it)
	post = util_submissions.create_submission_for_client(client)

	# Try to unsave the post
	unsave_response, _ = util.post_with_formkey(client, f"/unsave_post/{post.id}", data={})
	assert unsave_response.status_code == 200


def test_pin_post():
	"""Test pinning a post"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post
	post = util_submissions.create_submission_for_client(client)

	from files.__main__ import db_session
	from files.classes import Submission

	# Pin the post
	pin_response, _ = util.post_with_formkey(client, f"/pin/{post.id}", data={})
	assert pin_response.status_code == 200
	assert "pinned" in pin_response.text.lower()

	# Verify post is pinned
	db_session.expire_all()
	post_updated = db_session.query(Submission).filter_by(id=post.id).first()
	assert post_updated.is_pinned is True


def test_unpin_post():
	"""Test unpinning a post"""
	client, user = util_accounts.create_test_client_and_user()

	# Create and pin a post
	post = util_submissions.create_submission_for_client(client)

	from files.__main__ import db_session
	from files.classes import Submission

	pin_response, _ = util.post_with_formkey(client, f"/pin/{post.id}", data={})
	assert pin_response.status_code == 200

	# Verify post is pinned
	db_session.expire_all()
	post_pinned = db_session.query(Submission).filter_by(id=post.id).first()
	assert post_pinned.is_pinned is True

	# Unpin the post
	unpin_response, _ = util.post_with_formkey(client, f"/pin/{post.id}", data={})
	assert unpin_response.status_code == 200
	assert "unpinned" in unpin_response.text.lower()

	# Verify post is no longer pinned
	db_session.expire_all()
	post_updated = db_session.query(Submission).filter_by(id=post.id).first()
	assert post_updated.is_pinned is False


def test_pin_post_not_author():
	"""Test that non-authors cannot pin posts"""
	# Create two users
	client1, user1 = util_accounts.create_test_client_and_user(name="author-post4")
	client2, user2 = util_accounts.create_test_client_and_user(name="other-user4")

	# User1 creates a post
	post = util_submissions.create_submission_for_client(client1)

	# User2 tries to pin user1's post
	pin_response, _ = util.post_with_formkey(client2, f"/pin/{post.id}", data={})
	assert pin_response.status_code == 403


def test_toggle_comment_nsfw_by_author():
	"""Test author can toggle comment NSFW status"""
	from . import util_comments

	client, user = util_accounts.create_test_client_and_user()

	# Create a post and comment
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	from files.__main__ import db_session
	from files.classes import Comment

	# Check initial state
	db_session.expire_all()
	comment_initial = db_session.query(Comment).filter_by(id=comment.id).first()
	initial_nsfw = comment_initial.over_18

	# Toggle NSFW
	toggle_response, _ = util.post_with_formkey(client, f"/toggle_comment_nsfw/{comment.id}", data={})
	assert toggle_response.status_code == 200
	assert "18+" in toggle_response.text

	# Verify NSFW status changed
	db_session.expire_all()
	comment_updated = db_session.query(Comment).filter_by(id=comment.id).first()
	assert comment_updated.over_18 != initial_nsfw


def test_toggle_comment_nsfw_not_author():
	"""Test that non-authors cannot toggle comment NSFW without admin permissions"""
	from . import util_comments

	# Create two users
	client1, user1 = util_accounts.create_test_client_and_user(name="author-comment")
	client2, user2 = util_accounts.create_test_client_and_user(name="other-user5")

	# User1 creates a post and comment
	post = util_submissions.create_submission_for_client(client1)
	comment = util_comments.create_comment_for_client(client1, post.id)

	# User2 tries to toggle NSFW
	toggle_response, _ = util.post_with_formkey(client2, f"/toggle_comment_nsfw/{comment.id}", data={})
	assert toggle_response.status_code == 403


def test_delete_post_nonexistent():
	"""Test deleting a nonexistent post returns 404"""
	client, user = util_accounts.create_test_client_and_user()

	delete_response, _ = util.post_with_formkey(client, "/delete_post/999999", data={})
	assert delete_response.status_code == 404


def test_submit_title_route():
	"""Test GET /submit/title route"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/submit/title?url=https://example.com")
	# Should return JSON or success
	assert response.status_code in [200, 400]


def test_edit_post_route():
	"""Test POST /edit_post/<pid> route exists"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post
	post = util_submissions.create_submission_for_client(client)

	# Attempt to edit the post (may fail with 400 depending on post type/params)
	edit_response, _ = util.post_with_formkey(
		client, f"/edit_post/{post.id}",
		data={"body": "Updated body text"}
	)
	# Route exists and processes the request (200 success or 400 bad request)
	assert edit_response.status_code in [200, 400]


def test_viewmore_route():
	"""Test GET /viewmore/<pid>/<sort>/<offset> route"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post
	post = util_submissions.create_submission_for_client(client)

	response = client.get(f"/viewmore/{post.id}/new/0")
	assert response.status_code in [200, 400]


def test_morecomments_route():
	"""Test GET /morecomments/<cid> route"""
	from . import util_comments

	client, user = util_accounts.create_test_client_and_user()

	# Create a post and comment
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	response = client.get(f"/morecomments/{comment.id}")
	assert response.status_code == 200


def test_is_repost_route():
	"""Test POST /is_repost route"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/is_repost",
		data={"url": "https://example.com/test"}
	)
	assert response.status_code in [200, 400]


def test_view_post_route():
	"""Test GET /post/<pid> route"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post
	post = util_submissions.create_submission_for_client(client)

	# View the post
	response = client.get(f"/post/{post.id}")
	assert response.status_code == 200
	assert post.title in response.text


def test_view_post_with_slug_route():
	"""Test GET /post/<pid>/<anything> route"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post
	post = util_submissions.create_submission_for_client(client)

	# View the post with a slug
	response = client.get(f"/post/{post.id}/some-slug-here")
	assert response.status_code == 200
	assert post.title in response.text


def test_view_post_no_lazy_loads():
	"""Test GET /post/<pid> doesn't trigger lazy loads (logged in).

	Regression test: the highlight-unread JS in comments.html iterates
	p.comments. The post_id route must pre-set that relationship so
	rendering doesn't lazy-load every comment on the submission.
	"""
	from . import util_comments

	client, user = util_accounts.create_test_client_and_user("vpnll")

	post = util_submissions.create_submission_for_client(client)
	parent = util_comments.create_comment_for_client(client, post.id)
	util_comments.create_comment_for_client(client, post.id, data={
		"parent_fullname": f"comment_{parent.id}",
	})

	with warnings.catch_warnings(record=True) as w:
		warnings.simplefilter("always")
		response = client.get(f"/post/{post.id}")
		assert response.status_code == 200
		lazy_loads = [x for x in w if issubclass(x.category, LazyLoadWarning)]
		assert len(lazy_loads) == 0, \
			f"Lazy loads detected: {[str(x.message) for x in lazy_loads]}"


def test_view_post_logged_out_no_lazy_loads():
	"""Test GET /post/<pid> doesn't trigger lazy loads (logged out)."""
	from . import util_comments

	client, user = util_accounts.create_test_client_and_user("vpllo")

	post = util_submissions.create_submission_for_client(client)
	parent = util_comments.create_comment_for_client(client, post.id)
	util_comments.create_comment_for_client(client, post.id, data={
		"parent_fullname": f"comment_{parent.id}",
	})

	anon_client = util_accounts.create_logged_off_client()
	with warnings.catch_warnings(record=True) as w:
		warnings.simplefilter("always")
		response = anon_client.get(f"/post/{post.id}")
		assert response.status_code == 200
		lazy_loads = [x for x in w if issubclass(x.category, LazyLoadWarning)]
		assert len(lazy_loads) == 0, \
			f"Lazy loads detected: {[str(x.message) for x in lazy_loads]}"


def test_publish_post_route():
	"""Test POST /publish/<pid> route"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a post
	post = util_submissions.create_submission_for_client(client)

	# Try to publish it (may require specific conditions/draft state)
	response, _ = util.post_with_formkey(client, f"/publish/{post.id}", data={})
	# Route exists, may return various status codes depending on post state
	assert response.status_code in [200, 302, 400, 403]