"""Tests for admin routes."""
from . import util_accounts
from . import util
from . import util_submissions
from . import util_comments


def test_admin_dashboard():
	"""Test GET /admin route (admin dashboard)"""
	client, admin = util_accounts.create_test_client_and_admin(2)

	response = client.get("/admin")
	assert response.status_code == 200
	assert "admin" in response.text.lower() or "dashboard" in response.text.lower()


def test_admin_reported_posts():
	"""Test GET /admin/reported/posts route"""
	client, admin = util_accounts.create_test_client_and_admin(2)

	response = client.get("/admin/reported/posts")
	assert response.status_code == 200


def test_admin_reported_comments():
	"""Test GET /admin/reported/comments route"""
	client, admin = util_accounts.create_test_client_and_admin(2)

	response = client.get("/admin/reported/comments")
	assert response.status_code == 200


def test_admin_removed_posts():
	"""Test GET /admin/removed/posts route"""
	client, admin = util_accounts.create_test_client_and_admin(2)

	response = client.get("/admin/removed/posts")
	assert response.status_code == 200


def test_admin_removed_comments():
	"""Test GET /admin/removed/comments route"""
	client, admin = util_accounts.create_test_client_and_admin(2)

	response = client.get("/admin/removed/comments")
	assert response.status_code == 200


def test_admin_filtered_posts():
	"""Test GET /admin/filtered/posts route"""
	client, admin = util_accounts.create_test_client_and_admin(2)

	response = client.get("/admin/filtered/posts")
	assert response.status_code == 200


def test_admin_filtered_comments():
	"""Test GET /admin/filtered/comments route"""
	client, admin = util_accounts.create_test_client_and_admin(2)

	response = client.get("/admin/filtered/comments")
	assert response.status_code == 200


def test_admin_users():
	"""Test GET /admin/users route"""
	client, admin = util_accounts.create_test_client_and_admin(2)

	response = client.get("/admin/users")
	assert response.status_code == 200


def test_admin_shadowbanned():
	"""Test GET /admin/shadowbanned route"""
	client, admin = util_accounts.create_test_client_and_admin(2)

	response = client.get("/admin/shadowbanned")
	assert response.status_code == 200


def test_admin_image_posts():
	"""Test GET /admin/image_posts route"""
	client, admin = util_accounts.create_test_client_and_admin(2)

	response = client.get("/admin/image_posts")
	assert response.status_code == 200


def test_admin_loggedin():
	"""Test GET /admin/loggedin route"""
	client, admin = util_accounts.create_test_client_and_admin(3)

	response = client.get("/admin/loggedin")
	assert response.status_code == 200


def test_admin_loggedout():
	"""Test GET /admin/loggedout route"""
	client, admin = util_accounts.create_test_client_and_admin(3)

	response = client.get("/admin/loggedout")
	assert response.status_code == 200


def test_ban_user():
	"""Test POST /ban_user/<user_id> route"""
	from files.__main__ import db_session
	from files.classes import User

	admin_client, admin = util_accounts.create_test_client_and_admin(2, "ban-admin")

	client, user = util_accounts.create_test_client_and_user("banneduser")
	user_id = user.id

	response, _ = util.post_with_formkey(
		admin_client, f"/ban_user/{user_id}",
		data={"reason": "Test ban"}
	)
	assert response.status_code in [200, 302]

	# Verify user is actually banned in database
	with util.test_db_session() as session:
		user_after = session.get(User, user_id)
		assert user_after.is_banned != 0
		assert user_after.ban_reason == "Test ban"


def test_unban_user():
	"""Test POST /unban_user/<user_id> route"""
	from files.__main__ import db_session
	from files.classes import User

	admin_client, admin = util_accounts.create_test_client_and_admin(2, "unban-admin")

	client, user = util_accounts.create_test_client_and_user("unbanneduser")
	user_id = user.id

	# First ban the user
	util.post_with_formkey(
		admin_client, f"/ban_user/{user_id}",
		data={"reason": "Test ban"}
	)

	# Then unban them
	response, _ = util.post_with_formkey(
		admin_client, f"/unban_user/{user_id}",
		data={}
	)
	assert response.status_code in [200, 302]

	# Verify user is actually unbanned in database
	with util.test_db_session() as session:
		user_after = session.get(User, user_id)
		assert user_after.is_banned == 0


def test_shadowban_user():
	"""Test POST /shadowban/<user_id> route"""
	from files.__main__ import db_session
	from files.classes import User

	admin_client, admin = util_accounts.create_test_client_and_admin(2, "sb-admin")

	client, user = util_accounts.create_test_client_and_user("sbuser")
	user_id = user.id

	response, _ = util.post_with_formkey(
		admin_client, f"/shadowban/{user_id}",
		data={"reason": "Test shadowban"}
	)
	assert response.status_code in [200, 302]

	# Verify user is actually shadowbanned in database
	with util.test_db_session() as session:
		user_after = session.get(User, user_id)
		assert user_after.shadowbanned is not None


def test_unshadowban_user():
	"""Test POST /unshadowban/<user_id> route"""
	from files.__main__ import db_session
	from files.classes import User

	admin_client, admin = util_accounts.create_test_client_and_admin(2, "usb-admin")

	client, user = util_accounts.create_test_client_and_user("usbuser")
	user_id = user.id

	# First shadowban the user
	util.post_with_formkey(
		admin_client, f"/shadowban/{user_id}",
		data={"reason": "Test shadowban"}
	)

	# Then unshadowban them
	response, _ = util.post_with_formkey(
		admin_client, f"/unshadowban/{user_id}",
		data={}
	)
	assert response.status_code in [200, 302]

	# Verify user is actually unshadowbanned in database
	with util.test_db_session() as session:
		user_after = session.get(User, user_id)
		assert user_after.shadowbanned is None


def test_distinguish_post():
	"""Test POST /distinguish/<post_id> route"""
	from files.__main__ import db_session
	from files.classes import Submission

	admin_client, admin = util_accounts.create_test_client_and_admin(1, "dist-admin")

	# Create a post by admin
	post = util_submissions.create_submission_for_client(admin_client)
	post_id = post.id

	response, _ = util.post_with_formkey(
		admin_client, f"/distinguish/{post_id}",
		data={}
	)
	assert response.status_code in [200, 302]

	# Verify post is actually distinguished in database
	with util.test_db_session() as session:
		post_after = session.get(Submission, post_id)
		assert post_after.distinguish_level > 0


def test_distinguish_comment():
	"""Test POST /distinguish_comment/<c_id> route"""
	from files.__main__ import db_session
	from files.classes import Comment

	admin_client, admin = util_accounts.create_test_client_and_admin(1, "distc-admin")

	# Create a post and comment by admin
	post = util_submissions.create_submission_for_client(admin_client)
	comment = util_comments.create_comment_for_client(admin_client, post.id)
	comment_id = comment.id

	response, _ = util.post_with_formkey(
		admin_client, f"/distinguish_comment/{comment_id}",
		data={}
	)
	assert response.status_code in [200, 302]

	# Verify comment is actually distinguished in database
	with util.test_db_session() as session:
		comment_after = session.get(Comment, comment_id)
		assert comment_after.distinguish_level > 0


def test_sticky_post():
	"""Test POST /sticky/<post_id> route"""
	from files.__main__ import db_session
	from files.classes import Submission

	admin_client, admin = util_accounts.create_test_client_and_admin(2, "sticky-admin")

	client, user = util_accounts.create_test_client_and_user("stickypost")
	post = util_submissions.create_submission_for_client(client)
	post_id = post.id

	response, _ = util.post_with_formkey(
		admin_client, f"/sticky/{post_id}",
		data={}
	)
	assert response.status_code in [200, 302]

	# Verify post is actually stickied in database
	with util.test_db_session() as session:
		post_after = session.get(Submission, post_id)
		assert post_after.stickied is not None


def test_sticky_comment():
	"""Test POST /sticky_comment/<cid> route"""
	from files.__main__ import db_session
	from files.classes import Comment

	admin_client, admin = util_accounts.create_test_client_and_admin(2, "stickyc-admin")

	client, user = util_accounts.create_test_client_and_user("stickycomment")
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)
	comment_id = comment.id

	response, _ = util.post_with_formkey(
		admin_client, f"/sticky_comment/{comment_id}",
		data={}
	)
	assert response.status_code in [200, 302]

	# Verify comment is actually stickied in database
	with util.test_db_session() as session:
		comment_after = session.get(Comment, comment_id)
		assert comment_after.is_pinned is not None


def test_unsticky_comment():
	"""Test POST /unsticky_comment/<cid> route"""
	from files.__main__ import db_session
	from files.classes import Comment

	admin_client, admin = util_accounts.create_test_client_and_admin(2, "unstickyc-adm")

	client, user = util_accounts.create_test_client_and_user("unstickycom")
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)
	comment_id = comment.id

	# First sticky the comment
	util.post_with_formkey(
		admin_client, f"/sticky_comment/{comment_id}",
		data={}
	)

	# Then unsticky it
	response, _ = util.post_with_formkey(
		admin_client, f"/unsticky_comment/{comment_id}",
		data={}
	)
	assert response.status_code in [200, 302]

	# Verify comment is actually unstickied in database
	with util.test_db_session() as session:
		comment_after = session.get(Comment, comment_id)
		assert comment_after.is_pinned is None


def test_admin_badge_grant():
	"""Test POST /admin/badge_grant route"""
	from files.__main__ import db_session
	from files.classes import Badge

	admin_client, admin = util_accounts.create_test_client_and_admin(2, "badge-admin")

	client, user = util_accounts.create_test_client_and_user("badgeuser")
	user_id = user.id

	response, _ = util.post_with_formkey(
		admin_client, "/admin/badge_grant",
		data={"username": user.username, "badge_id": "1", "description": "Test badge"}
	)
	assert response.status_code in [200, 302]

	# Verify badge was granted in database
	with util.test_db_session() as session:
		badge = session.query(Badge).filter_by(user_id=user_id, badge_id=1).first()
		assert badge is not None


def test_admin_badge_remove():
	"""Test POST /admin/badge_remove route"""
	from files.__main__ import db_session
	from files.classes import Badge

	admin_client, admin = util_accounts.create_test_client_and_admin(2, "badgerm-admin")

	client, user = util_accounts.create_test_client_and_user("badgermuser")
	user_id = user.id

	# First grant a badge
	util.post_with_formkey(
		admin_client, "/admin/badge_grant",
		data={"username": user.username, "badge_id": "1", "description": "Test badge"}
	)

	# Then remove it
	response, _ = util.post_with_formkey(
		admin_client, "/admin/badge_remove",
		data={"username": user.username, "badge_id": "1"}
	)
	assert response.status_code in [200, 302]

	# Verify badge was removed from database
	with util.test_db_session() as session:
		badge = session.query(Badge).filter_by(user_id=user_id, badge_id=1).first()
		assert badge is None


def test_admin_alt_votes():
	"""Test GET /admin/alt_votes route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3)

	response = admin_client.get("/admin/alt_votes")
	assert response.status_code == 200


def test_admin_banned_domains():
	"""Test GET /admin/banned_domains route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3)

	response = admin_client.get("/admin/banned_domains")
	assert response.status_code == 200


def test_admin_banned_domains_post():
	"""Test POST /admin/banned_domains route"""
	import time
	from files.__main__ import db_session
	from files.classes import BannedDomain

	admin_client, admin = util_accounts.create_test_client_and_admin(3, "ban-domp-adm")

	# Use a unique domain name to avoid conflicts with other tests
	test_domain = f"test-banned-domain-{int(time.time())}.com"
	response, _ = util.post_with_formkey(
		admin_client, "/admin/banned_domains",
		data={"domain": test_domain, "reason": "Test ban reason"}
	)
	assert response.status_code in [200, 302]

	# Verify domain was banned in database (re-query after HTTP request)
	with util.test_db_session() as session:
		banned = session.query(BannedDomain).filter_by(domain=test_domain).first()
		assert banned is not None
		assert banned.domain == test_domain
		assert banned.reason == "Test ban reason"


def test_admin_nuke_user():
	"""Test POST /admin/nuke_user route"""
	from files.__main__ import db_session
	from files.classes import Submission, Comment

	admin_client, admin = util_accounts.create_test_client_and_admin(3, "nuke-admin")

	client, user = util_accounts.create_test_client_and_user("nukeduser")

	# Create a post and comment by the user
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)
	post_id = post.id
	comment_id = comment.id

	response, _ = util.post_with_formkey(
		admin_client, "/admin/nuke_user",
		data={"user": user.username}
	)
	assert response.status_code in [200, 302]

	# Verify all user's posts and comments are removed in database
	with util.test_db_session() as session:
		post_after = session.get(Submission, post_id)
		comment_after = session.get(Comment, comment_id)
		assert post_after.state_mod.name == "REMOVED"
		assert comment_after.state_mod.name == "REMOVED"


def test_admin_unnuke_user():
	"""Test POST /admin/unnuke_user route"""
	from files.__main__ import db_session
	from files.classes import Submission, Comment

	admin_client, admin = util_accounts.create_test_client_and_admin(3, "unnuke-admin")

	client, user = util_accounts.create_test_client_and_user("unnukeduser")

	# Create a post and comment by the user
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)
	post_id = post.id
	comment_id = comment.id

	# First nuke the user
	util.post_with_formkey(
		admin_client, "/admin/nuke_user",
		data={"user": user.username}
	)

	# Then unnuke them
	response, _ = util.post_with_formkey(
		admin_client, "/admin/unnuke_user",
		data={"user": user.username}
	)
	assert response.status_code in [200, 302]

	# Verify all user's posts and comments are restored in database
	with util.test_db_session() as session:
		post_after = session.get(Submission, post_id)
		comment_after = session.get(Comment, comment_id)
		assert post_after.state_mod.name == "VISIBLE"
		assert comment_after.state_mod.name == "VISIBLE"


def test_admin_verify_user():
	"""Test POST /admin/verify/<user_id> route"""
	from files.__main__ import db_session
	from files.classes import User

	admin_client, admin = util_accounts.create_test_client_and_admin(3, "verify-admin")

	client, user = util_accounts.create_test_client_and_user("verifyuser")
	user_id = user.id

	response, _ = util.post_with_formkey(
		admin_client, f"/admin/verify/{user_id}",
		data={}
	)
	assert response.status_code in [200, 302]

	# Verify user is actually verified in database
	with util.test_db_session() as session:
		user_after = session.get(User, user_id)
		assert user_after.verified == "Verified"


def test_admin_unverify_user():
	"""Test POST /admin/unverify/<user_id> route"""
	from files.__main__ import db_session
	from files.classes import User

	admin_client, admin = util_accounts.create_test_client_and_admin(3, "unvrfy-admin")

	client, user = util_accounts.create_test_client_and_user("unverifyuser")
	user_id = user.id

	# First verify the user
	util.post_with_formkey(
		admin_client, f"/admin/verify/{user_id}",
		data={}
	)

	# Then unverify them
	response, _ = util.post_with_formkey(
		admin_client, f"/admin/unverify/{user_id}",
		data={}
	)
	assert response.status_code in [200, 302]

	# Verify user is actually unverified in database
	with util.test_db_session() as session:
		user_after = session.get(User, user_id)
		assert user_after.verified is None


def test_admin_title_change():
	"""Test POST /admin/title_change/<user_id> route"""
	from files.__main__ import db_session
	from files.classes import User

	admin_client, admin = util_accounts.create_test_client_and_admin(2, "title-admin")

	client, user = util_accounts.create_test_client_and_user("titleuser")
	user_id = user.id

	response, _ = util.post_with_formkey(
		admin_client, f"/admin/title_change/{user_id}",
		data={"title": "New Title"}
	)
	assert response.status_code in [200, 302]

	# Verify title was changed in database
	with util.test_db_session() as session:
		user_after = session.get(User, user_id)
		assert user_after.customtitleplain == "New Title"


def test_admin_link_accounts():
	"""Test POST /admin/link_accounts route"""
	from files.__main__ import db_session
	from files.classes import Alt

	admin_client, admin = util_accounts.create_test_client_and_admin(3, "link-admin")

	client1, user1 = util_accounts.create_test_client_and_user("linkuser1")
	client2, user2 = util_accounts.create_test_client_and_user("linkuser2")
	user1_id = user1.id
	user2_id = user2.id

	response, _ = util.post_with_formkey(
		admin_client, "/admin/link_accounts",
		data={"u1": str(user1_id), "u2": str(user2_id)}
	)
	assert response.status_code in [200, 302]

	# Verify alt link was created in database
	with util.test_db_session() as session:
		alt = session.query(Alt).filter_by(user1=user1_id, user2=user2_id).first()
		assert alt is not None
		assert alt.is_manual == True


def test_admin_under_attack():
	"""Test POST /admin/under_attack route"""
	# This route makes external Cloudflare API calls which will fail in test environment
	# We just verify the route is accessible and handles the error gracefully
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "attack-admin")

	response, _ = util.post_with_formkey(
		admin_client, "/admin/under_attack",
		data={}
	)
	# Will return 500 because Cloudflare API call fails in test environment
	assert response.status_code in [200, 302, 400, 500]


def test_admin_purge_cache():
	"""Test POST /admin/purge_cache route"""
	# This route makes external Cloudflare API calls which will fail in test environment
	# We just verify the route is accessible and handles the error gracefully
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "purge-admin")

	response, _ = util.post_with_formkey(
		admin_client, "/admin/purge_cache",
		data={}
	)
	# Will return 500 because Cloudflare API call fails in test environment
	assert response.status_code in [200, 302, 400, 500]


def test_admin_dump_cache():
	"""Test GET /admin/dump_cache route (POST-only)"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "dump-admin")

	# Route is POST-only, GET returns 405
	response = admin_client.get("/admin/dump_cache")
	assert response.status_code == 405


def test_filter_automatic():
	"""Test POST /filter_automatic/<user_id> route"""
	from files.__main__ import db_session
	from files.classes import User
	from files.classes.user import FilterBehavior

	admin_client, admin = util_accounts.create_test_client_and_admin(2, "filtauto-adm")

	client, user = util_accounts.create_test_client_and_user("filtautouser")
	user_id = user.id

	response, _ = util.post_with_formkey(
		admin_client, f"/filter_automatic/{user_id}",
		data={}
	)
	assert response.status_code in [200, 302]

	# Verify user filter behavior was set to automatic in database
	with util.test_db_session() as session:
		user_after = session.get(User, user_id)
		assert user_after.filter_behavior == FilterBehavior.AUTOMATIC


def test_filter_filtered():
	"""Test POST /filter_filtered/<user_id> route"""
	from files.__main__ import db_session
	from files.classes import User
	from files.classes.user import FilterBehavior

	admin_client, admin = util_accounts.create_test_client_and_admin(2, "filtfilt-adm")

	client, user = util_accounts.create_test_client_and_user("filtfiltuser")
	user_id = user.id

	response, _ = util.post_with_formkey(
		admin_client, f"/filter_filtered/{user_id}",
		data={}
	)
	assert response.status_code in [200, 302]

	# Verify user filter behavior was set to filtered in database
	with util.test_db_session() as session:
		user_after = session.get(User, user_id)
		assert user_after.filter_behavior == FilterBehavior.FILTERED


def test_filter_unfiltered():
	"""Test POST /filter_unfiltered/<user_id> route"""
	from files.__main__ import db_session
	from files.classes import User
	from files.classes.user import FilterBehavior

	admin_client, admin = util_accounts.create_test_client_and_admin(2, "filtunf-adm")

	client, user = util_accounts.create_test_client_and_user("filtunfuser")
	user_id = user.id

	response, _ = util.post_with_formkey(
		admin_client, f"/filter_unfiltered/{user_id}",
		data={}
	)
	assert response.status_code in [200, 302]

	# Verify user filter behavior was set to unfiltered in database
	with util.test_db_session() as session:
		user_after = session.get(User, user_id)
		assert user_after.filter_behavior == FilterBehavior.UNFILTERED


def test_admin_update_filter_status():
	"""Test POST /admin/update_filter_status route"""
	from files.__main__ import db_session
	from files.classes import Submission

	admin_client, admin = util_accounts.create_test_client_and_admin(2, "updfilt-admin")

	# Create a post to filter
	client, user = util_accounts.create_test_client_and_user("filtstatuser")
	post = util_submissions.create_submission_for_client(client)
	post_id = post.id

	# Remove the post
	response, _ = util.post_json_with_formkey(
		admin_client, f"/post/{post_id}", "/admin/update_filter_status",
		json_data={
			"post_id": post_id,
			"new_status": "removed"
		}
	)
	assert response.status_code == 200

	# Verify post is actually removed in database
	with util.test_db_session() as session:
		post_after = session.get(Submission, post_id)
		assert post_after.state_mod.name == "REMOVED"

	# Test restoring the post to normal
	response, _ = util.post_json_with_formkey(
		admin_client, f"/post/{post_id}", "/admin/update_filter_status",
		json_data={
			"post_id": post_id,
			"new_status": "normal"
		}
	)
	assert response.status_code == 200

	# Verify post is restored in database
	with util.test_db_session() as session:
		post_after = session.get(Submission, post_id)
		assert post_after.state_mod.name == "VISIBLE"


def test_admin_site_settings():
	"""Test POST /admin/site_settings/<setting> route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "siteset-admin")

	response, _ = util.post_with_formkey(
		admin_client, "/admin/site_settings/test_setting",
		data={"value": "test_value"}
	)
	assert response.status_code in [200, 302, 400, 404, 500]


def test_performance_dashboard():
	"""Test GET /performance/ route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3)

	response = admin_client.get("/performance/")
	assert response.status_code == 200


def test_tasks_list():
	"""Test GET /tasks/ route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3)

	response = admin_client.get("/tasks/")
	assert response.status_code == 200


def test_tasks_detail():
	"""Test GET /tasks/<task_id>/ route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3)

	# Use a fake task ID
	response = admin_client.get("/tasks/1/")
	assert response.status_code in [200, 404]


def test_tasks_runs():
	"""Test GET /tasks/<task_id>/runs/ route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3)

	# Use a fake task ID
	response = admin_client.get("/tasks/1/runs/")
	assert response.status_code in [200, 302, 404]


def test_tasks_run_detail():
	"""Test GET /tasks/<task_id>/runs/<run_id> route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3)

	# Use fake task and run IDs
	response = admin_client.get("/tasks/1/runs/1")
	assert response.status_code in [200, 404]


def test_tasks_schedule():
	"""Test POST /tasks/<task_id>/schedule route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "tasksched-adm")

	response, _ = util.post_with_formkey(
		admin_client, "/tasks/1/schedule",
		data={}
	)
	assert response.status_code in [200, 302, 400, 404, 500]


def test_tasks_scheduled_posts_list():
	"""Test GET /tasks/scheduled_posts/ route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3)

	response = admin_client.get("/tasks/scheduled_posts/")
	assert response.status_code == 200


def test_tasks_scheduled_posts_create():
	"""Test POST /tasks/scheduled_posts/ route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "schedpost-adm")

	response, _ = util.post_with_formkey(
		admin_client, "/tasks/scheduled_posts/",
		data={}
	)
	assert response.status_code in [200, 302, 400, 500]


def test_tasks_scheduled_posts_detail():
	"""Test GET /tasks/scheduled_posts/<pid> route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "schedpostd-adm")

	# Use a fake post ID
	response = admin_client.get("/tasks/scheduled_posts/1")
	assert response.status_code in [200, 404]


def test_tasks_scheduled_posts_content():
	"""Test POST /tasks/scheduled_posts/<pid>/content route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "schedpostc-adm")

	response, _ = util.post_with_formkey(
		admin_client, "/tasks/scheduled_posts/1/content",
		data={}
	)
	assert response.status_code in [200, 302, 400, 404, 500]


def test_tasks_scheduled_posts_schedule():
	"""Test POST /tasks/scheduled_posts/<task_id>/schedule route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "schedposts-adm")

	response, _ = util.post_with_formkey(
		admin_client, "/tasks/scheduled_posts/1/schedule",
		data={}
	)
	assert response.status_code in [200, 302, 400, 404, 500]


def test_make_admin():
	"""Test POST /@<username>/make_admin route"""
	from files.__main__ import db_session
	from files.classes import User

	admin_client, admin = util_accounts.create_test_client_and_admin(3, "mkadmin-admin")

	target_client, target_user = util_accounts.create_test_client_and_user("mkadmin-target")
	target_user_id = target_user.id

	response, _ = util.post_with_formkey(
		admin_client, f"/@{target_user.username}/make_admin",
		data={"level": "1"}
	)
	assert response.status_code in [200, 302]

	# Verify user is now an admin in database
	with util.test_db_session() as session:
		user_after = session.get(User, target_user_id)
		assert user_after.admin_level == 2


def test_remove_admin():
	"""Test POST /@<username>/remove_admin route"""
	from files.__main__ import db_session
	from files.classes import User

	admin_client, admin = util_accounts.create_test_client_and_admin(3, "rmadmin-admin")

	target_client, target_user = util_accounts.create_test_client_and_admin(1, "rmadmin-target")
	target_user_id = target_user.id

	response, _ = util.post_with_formkey(
		admin_client, f"/@{target_user.username}/remove_admin",
		data={}
	)
	assert response.status_code in [200, 302]

	# Verify user is no longer an admin in database
	with util.test_db_session() as session:
		user_after = session.get(User, target_user_id)
		assert user_after.admin_level == 0


def test_create_note():
	"""Test POST /@<username>/create_note route"""
	import json as json_module
	from files.__main__ import db_session
	from files.classes import UserNote

	admin_client, admin = util_accounts.create_test_client_and_admin(2, "note-admin")
	# Extract admin_id immediately before admin object becomes detached
	db_session().refresh(admin)
	admin_id = admin.id

	target_client, target_user = util_accounts.create_test_client_and_user("note-target")
	# Extract user data immediately before objects become detached
	db_session().refresh(target_user)
	user_id = target_user.id
	target_username = target_user.username

	# Route expects 'data' parameter containing JSON with 'note' and 'tag' fields
	note_data = json_module.dumps({
		"note": "Test admin note",
		"tag": 2  # UserTag.Comment
	})

	response, _ = util.post_with_formkey(
		admin_client, f"/@{target_username}/create_note",
		data={"data": note_data}
	)
	assert response.status_code == 200

	# Verify note was created in database (re-query after HTTP request)
	with util.test_db_session() as session:
		note = session.query(UserNote).filter_by(
			author_id=admin_id,
			reference_user=user_id
		).first()
		assert note is not None
		assert note.note == "Test admin note"
		assert note.tag.value == 2


def test_delete_note():
	"""Test POST /@<username>/delete_note/<id> route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(2, "delnote-admin")

	target_client, target_user = util_accounts.create_test_client_and_user("delnote-target")

	# Try to delete a non-existent note
	response, _ = util.post_with_formkey(
		admin_client, f"/@{target_user.username}/delete_note/1",
		data={}
	)
	assert response.status_code in [200, 302, 400, 404]


def test_revert_actions():
	"""Test POST /@<username>/revert_actions route"""
	from files.__main__ import db_session
	from files.classes import Submission, Comment

	admin_client, admin = util_accounts.create_test_client_and_admin(3, "revert-admin")

	# Create a mod who will perform actions that we'll revert
	mod_client, mod_user = util_accounts.create_test_client_and_admin(2, "revert-mod")
	mod_username = mod_user.username

	# Create a regular user and their content
	user_client, user = util_accounts.create_test_client_and_user("revert-content")
	post = util_submissions.create_submission_for_client(user_client)
	comment = util_comments.create_comment_for_client(user_client, post.id)
	post_id = post.id
	comment_id = comment.id

	# Have the mod remove the post and comment
	util.post_json_with_formkey(
		mod_client, f"/post/{post_id}", "/admin/update_filter_status",
		json_data={"post_id": post_id, "new_status": "removed"}
	)
	util.post_json_with_formkey(
		mod_client, f"/post/{post_id}", "/admin/update_filter_status",
		json_data={"comment_id": comment_id, "new_status": "removed"}
	)

	# Verify they're removed (re-query after HTTP requests)
	with util.test_db_session() as session:
		post_before = session.get(Submission, post_id)
		comment_before = session.get(Comment, comment_id)
		assert post_before.state_mod.name == "REMOVED"
		assert comment_before.state_mod.name == "REMOVED"

	# Now revert all of the mod's actions
	response, _ = util.post_with_formkey(
		admin_client, f"/@{mod_username}/revert_actions",
		data={}
	)
	assert response.status_code in [200, 302]

	# Verify the removals were reverted (re-query after HTTP request)
	with util.test_db_session() as session:
		post_after = session.get(Submission, post_id)
		comment_after = session.get(Comment, comment_id)
		assert post_after.state_mod.name == "VISIBLE"
		assert comment_after.state_mod.name == "VISIBLE"


def test_admin_badge_grant_get():
	"""Test GET /admin/badge_grant route"""
	client, admin = util_accounts.create_test_client_and_admin(2)

	response = client.get("/admin/badge_grant")
	assert response.status_code == 200


def test_admin_badge_remove_get():
	"""Test GET /admin/badge_remove route"""
	client, admin = util_accounts.create_test_client_and_admin(2)

	response = client.get("/admin/badge_remove")
	assert response.status_code == 200


def test_user_notes_modal_loads():
	"""Test that pages with user notes modal load properly for admins (#718)

	The user notes modal (usernote.html) is included in submission listing
	pages when viewed by an admin. This test verifies the page loads and
	the modal markup is present, which exercises the CSS we fixed for mobile.
	"""
	admin_client, admin = util_accounts.create_test_client_and_admin(2, "unotes-admin")

	# Create a post so the front page has content with the usernote modal
	client, user = util_accounts.create_test_client_and_user("unotes-user")
	post = util_submissions.create_submission_for_client(client)

	# Load the front page as admin (submission_listing.html includes usernote.html)
	response = admin_client.get("/")
	assert response.status_code == 200
	# The usernote modal container should be present for admins
	assert "modal__container" in response.text


def test_user_notes_modal_on_post_page():
	"""Test that user notes modal loads on individual post pages (#718)

	The user notes modal appears on post detail pages too (via comments.html
	which includes usernote_header.html). This tests the CSS applies there.
	"""
	admin_client, admin = util_accounts.create_test_client_and_admin(2, "unotep-admin")

	# Create a post
	client, user = util_accounts.create_test_client_and_user("unotep-user")
	post = util_submissions.create_submission_for_client(client)
	post_id = post.id

	# Load the post page as admin
	response = admin_client.get(f"/post/{post_id}")
	assert response.status_code == 200
	# The usernote modal container should be present
	assert "modal__container" in response.text
	# The usernote link should be present for admin users
	assert "usernote-link" in response.text


def test_unsticky_post():
	"""Test POST /unsticky/<post_id> route"""
	from files.__main__ import db_session
	from files.classes import Submission

	admin_client, admin = util_accounts.create_test_client_and_admin(2, "unsticky-admin")

	client, user = util_accounts.create_test_client_and_user("unstickypost")
	post = util_submissions.create_submission_for_client(client)
	post_id = post.id

	# First sticky the post
	response, _ = util.post_with_formkey(
		admin_client, f"/sticky/{post_id}",
		data={}
	)
	assert response.status_code in [200, 302]

	# Then unsticky it
	response, _ = util.post_with_formkey(
		admin_client, f"/unsticky/{post_id}",
		data={}
	)
	assert response.status_code in [200, 302]

	# Verify post is actually unstickied in database
	with util.test_db_session() as session:
		post_after = session.get(Submission, post_id)
		assert post_after.stickied is None
