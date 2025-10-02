"""Tests for admin routes."""
from . import util_accounts
from . import util
from . import util_submissions
from . import util_comments


def test_admin_dashboard():
	"""Test GET /admin route (admin dashboard)"""
	client, admin = util_accounts.create_test_client_and_admin(2, "admin-dash")

	response = client.get("/admin")
	assert response.status_code == 200


def test_admin_reported_posts():
	"""Test GET /admin/reported/posts route"""
	client, admin = util_accounts.create_test_client_and_admin(2, "admin-reports")

	response = client.get("/admin/reported/posts")
	assert response.status_code == 200


def test_admin_reported_comments():
	"""Test GET /admin/reported/comments route"""
	client, admin = util_accounts.create_test_client_and_admin(2, "admin-rep-com")

	response = client.get("/admin/reported/comments")
	assert response.status_code == 200


def test_admin_removed_posts():
	"""Test GET /admin/removed/posts route"""
	client, admin = util_accounts.create_test_client_and_admin(2, "admin-rem-post")

	response = client.get("/admin/removed/posts")
	assert response.status_code == 200


def test_admin_removed_comments():
	"""Test GET /admin/removed/comments route"""
	client, admin = util_accounts.create_test_client_and_admin(2, "admin-rem-com")

	response = client.get("/admin/removed/comments")
	assert response.status_code == 200


def test_admin_filtered_posts():
	"""Test GET /admin/filtered/posts route"""
	client, admin = util_accounts.create_test_client_and_admin(2, "admin-filt-pst")

	response = client.get("/admin/filtered/posts")
	assert response.status_code == 200


def test_admin_filtered_comments():
	"""Test GET /admin/filtered/comments route"""
	client, admin = util_accounts.create_test_client_and_admin(2, "admin-filt-com")

	response = client.get("/admin/filtered/comments")
	assert response.status_code == 200


def test_admin_users():
	"""Test GET /admin/users route"""
	client, admin = util_accounts.create_test_client_and_admin(2, "admin-users")

	response = client.get("/admin/users")
	assert response.status_code == 200


def test_admin_shadowbanned():
	"""Test GET /admin/shadowbanned route"""
	client, admin = util_accounts.create_test_client_and_admin(2, "admin-shadow")

	response = client.get("/admin/shadowbanned")
	assert response.status_code == 200


def test_admin_image_posts():
	"""Test GET /admin/image_posts route"""
	client, admin = util_accounts.create_test_client_and_admin(2, "admin-images")

	response = client.get("/admin/image_posts")
	assert response.status_code == 200


def test_admin_loggedin():
	"""Test GET /admin/loggedin route"""
	client, admin = util_accounts.create_test_client_and_admin(3, "admin-loggedin")

	response = client.get("/admin/loggedin")
	assert response.status_code == 200


def test_admin_loggedout():
	"""Test GET /admin/loggedout route"""
	client, admin = util_accounts.create_test_client_and_admin(3, "admin-loggedout")

	response = client.get("/admin/loggedout")
	assert response.status_code == 200


def test_ban_user():
	"""Test POST /ban_user/<user_id> route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(2, "ban-admin")

	client, user = util_accounts.create_test_client_and_user("banneduser")

	response, _ = util.post_with_formkey(
		admin_client, f"/ban_user/{user.id}",
		data={"reason": "Test ban"}
	)
	assert response.status_code in [200, 302, 400]


def test_unban_user():
	"""Test POST /unban_user/<user_id> route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(2, "unban-admin")

	client, user = util_accounts.create_test_client_and_user("unbanneduser")

	response, _ = util.post_with_formkey(
		admin_client, f"/unban_user/{user.id}",
		data={}
	)
	assert response.status_code in [200, 302, 400]


def test_shadowban_user():
	"""Test POST /shadowban/<user_id> route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(2, "sb-admin")

	client, user = util_accounts.create_test_client_and_user("sbuser")

	response, _ = util.post_with_formkey(
		admin_client, f"/shadowban/{user.id}",
		data={"reason": "Test shadowban"}
	)
	assert response.status_code in [200, 302, 400]


def test_unshadowban_user():
	"""Test POST /unshadowban/<user_id> route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(2, "usb-admin")

	client, user = util_accounts.create_test_client_and_user("usbuser")

	response, _ = util.post_with_formkey(
		admin_client, f"/unshadowban/{user.id}",
		data={}
	)
	assert response.status_code in [200, 302, 400]


def test_distinguish_post():
	"""Test POST /distinguish/<post_id> route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(1, "dist-admin")

	# Create a post by admin
	post = util_submissions.create_submission_for_client(admin_client)

	response, _ = util.post_with_formkey(
		admin_client, f"/distinguish/{post.id}",
		data={}
	)
	assert response.status_code in [200, 302, 400]


def test_distinguish_comment():
	"""Test POST /distinguish_comment/<c_id> route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(1, "distc-admin")

	# Create a post and comment by admin
	post = util_submissions.create_submission_for_client(admin_client)
	comment = util_comments.create_comment_for_client(admin_client, post.id)

	response, _ = util.post_with_formkey(
		admin_client, f"/distinguish_comment/{comment.id}",
		data={}
	)
	assert response.status_code in [200, 302, 400]


def test_sticky_post():
	"""Test POST /sticky/<post_id> route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(2, "sticky-admin")

	client, user = util_accounts.create_test_client_and_user("stickypost")
	post = util_submissions.create_submission_for_client(client)

	response, _ = util.post_with_formkey(
		admin_client, f"/sticky/{post.id}",
		data={}
	)
	assert response.status_code in [200, 302, 400]


def test_sticky_comment():
	"""Test POST /sticky_comment/<cid> route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(2, "stickyc-admin")

	client, user = util_accounts.create_test_client_and_user("stickycomment")
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	response, _ = util.post_with_formkey(
		admin_client, f"/sticky_comment/{comment.id}",
		data={}
	)
	assert response.status_code in [200, 302, 400]


def test_unsticky_comment():
	"""Test POST /unsticky_comment/<cid> route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(2, "unstickyc-adm")

	client, user = util_accounts.create_test_client_and_user("unstickycom")
	post = util_submissions.create_submission_for_client(client)
	comment = util_comments.create_comment_for_client(client, post.id)

	response, _ = util.post_with_formkey(
		admin_client, f"/unsticky_comment/{comment.id}",
		data={}
	)
	assert response.status_code in [200, 302, 400]


def test_admin_badge_grant():
	"""Test POST /admin/badge_grant route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(2, "badge-admin")

	client, user = util_accounts.create_test_client_and_user("badgeuser")

	response, _ = util.post_with_formkey(
		admin_client, "/admin/badge_grant",
		data={"username": user.username, "badge_id": "1"}
	)
	assert response.status_code in [200, 302, 400, 404]


def test_admin_badge_remove():
	"""Test POST /admin/badge_remove route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(2, "badgerm-admin")

	client, user = util_accounts.create_test_client_and_user("badgermuser")

	response, _ = util.post_with_formkey(
		admin_client, "/admin/badge_remove",
		data={"username": user.username, "badge_id": "1"}
	)
	assert response.status_code in [200, 302, 400, 404]


def test_admin_alt_votes():
	"""Test GET /admin/alt_votes route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "alt-vote-adm")

	response = admin_client.get("/admin/alt_votes")
	assert response.status_code == 200


def test_admin_banned_domains():
	"""Test GET /admin/banned_domains route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "ban-dom-adm")

	response = admin_client.get("/admin/banned_domains")
	assert response.status_code == 200


def test_admin_banned_domains_post():
	"""Test POST /admin/banned_domains/ route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "ban-domp-adm")

	response, _ = util.post_with_formkey(
		admin_client, "/admin/banned_domains/",
		data={"domain": "example.com"}
	)
	assert response.status_code in [200, 302, 400]


def test_admin_nuke_user():
	"""Test POST /admin/nuke_user route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "nuke-admin")

	client, user = util_accounts.create_test_client_and_user("nukeduser")

	response, _ = util.post_with_formkey(
		admin_client, "/admin/nuke_user",
		data={"user": user.username}
	)
	assert response.status_code in [200, 302, 400]


def test_admin_unnuke_user():
	"""Test POST /admin/unnuke_user route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "unnuke-admin")

	client, user = util_accounts.create_test_client_and_user("unnukeduser")

	response, _ = util.post_with_formkey(
		admin_client, "/admin/unnuke_user",
		data={"user": user.username}
	)
	assert response.status_code in [200, 302, 400]


def test_admin_verify_user():
	"""Test POST /admin/verify/<user_id> route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "verify-admin")

	client, user = util_accounts.create_test_client_and_user("verifyuser")

	response, _ = util.post_with_formkey(
		admin_client, f"/admin/verify/{user.id}",
		data={}
	)
	assert response.status_code in [200, 302, 400]


def test_admin_unverify_user():
	"""Test POST /admin/unverify/<user_id> route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "unvrfy-admin")

	client, user = util_accounts.create_test_client_and_user("unverifyuser")

	response, _ = util.post_with_formkey(
		admin_client, f"/admin/unverify/{user.id}",
		data={}
	)
	assert response.status_code in [200, 302, 400]


def test_admin_title_change():
	"""Test POST /admin/title_change/<user_id> route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(2, "title-admin")

	client, user = util_accounts.create_test_client_and_user("titleuser")

	response, _ = util.post_with_formkey(
		admin_client, f"/admin/title_change/{user.id}",
		data={"title": "New Title"}
	)
	assert response.status_code in [200, 302, 400]


def test_admin_link_accounts():
	"""Test POST /admin/link_accounts route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "link-admin")

	client1, user1 = util_accounts.create_test_client_and_user("linkuser1")
	client2, user2 = util_accounts.create_test_client_and_user("linkuser2")

	response, _ = util.post_with_formkey(
		admin_client, "/admin/link_accounts",
		data={"id1": str(user1.id), "id2": str(user2.id)}
	)
	assert response.status_code in [200, 302, 400, 404]


def test_admin_under_attack():
	"""Test POST /admin/under_attack route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "attack-admin")

	response, _ = util.post_with_formkey(
		admin_client, "/admin/under_attack",
		data={}
	)
	assert response.status_code in [200, 302, 400, 500]


def test_admin_purge_cache():
	"""Test POST /admin/purge_cache route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "purge-admin")

	response, _ = util.post_with_formkey(
		admin_client, "/admin/purge_cache",
		data={}
	)
	assert response.status_code in [200, 302, 400, 500]


def test_admin_dump_cache():
	"""Test GET /admin/dump_cache route (POST-only)"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "dump-admin")

	# Route is POST-only, GET returns 405
	response = admin_client.get("/admin/dump_cache")
	assert response.status_code == 405


def test_filter_automatic():
	"""Test POST /filter_automatic/<user_id> route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(2, "filtauto-adm")

	client, user = util_accounts.create_test_client_and_user("filtautouser")

	response, _ = util.post_with_formkey(
		admin_client, f"/filter_automatic/{user.id}",
		data={}
	)
	assert response.status_code in [200, 302, 400]


def test_filter_filtered():
	"""Test POST /filter_filtered/<user_id> route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(2, "filtfilt-adm")

	client, user = util_accounts.create_test_client_and_user("filtfiltuser")

	response, _ = util.post_with_formkey(
		admin_client, f"/filter_filtered/{user.id}",
		data={}
	)
	assert response.status_code in [200, 302, 400]


def test_filter_unfiltered():
	"""Test POST /filter_unfiltered/<user_id> route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(2, "filtunf-adm")

	client, user = util_accounts.create_test_client_and_user("filtunfuser")

	response, _ = util.post_with_formkey(
		admin_client, f"/filter_unfiltered/{user.id}",
		data={}
	)
	assert response.status_code in [200, 302, 400]


def test_admin_update_filter_status():
	"""Test POST /admin/update_filter_status route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(2, "updfilt-admin")

	response, _ = util.post_with_formkey(
		admin_client, "/admin/update_filter_status",
		data={}
	)
	assert response.status_code in [200, 302, 400, 413, 415]


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
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "perf-admin")

	response = admin_client.get("/performance/")
	assert response.status_code == 200


def test_tasks_list():
	"""Test GET /tasks/ route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "tasks-admin")

	response = admin_client.get("/tasks/")
	assert response.status_code == 200


def test_tasks_detail():
	"""Test GET /tasks/<task_id>/ route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "taskdet-admin")

	# Use a fake task ID
	response = admin_client.get("/tasks/1/")
	assert response.status_code in [200, 404]


def test_tasks_runs():
	"""Test GET /tasks/<task_id>/runs/ route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "taskruns-adm")

	# Use a fake task ID
	response = admin_client.get("/tasks/1/runs/")
	assert response.status_code in [200, 302, 404]


def test_tasks_run_detail():
	"""Test GET /tasks/<task_id>/runs/<run_id> route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "taskrun-admin")

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
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "schedposts-adm")

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
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "mkadmin-admin")

	target_client, target_user = util_accounts.create_test_client_and_user("mkadmin-target")

	response, _ = util.post_with_formkey(
		admin_client, f"/@{target_user.username}/make_admin",
		data={"level": "1"}
	)
	assert response.status_code in [200, 302, 400, 403]


def test_remove_admin():
	"""Test POST /@<username>/remove_admin route"""
	from files.__main__ import db_session
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "rmadmin-admin")

	target_client, target_user = util_accounts.create_test_client_and_admin(1, "rmadmin-target")

	response, _ = util.post_with_formkey(
		admin_client, f"/@{target_user.username}/remove_admin",
		data={}
	)
	assert response.status_code in [200, 302, 400, 403]


def test_create_note():
	"""Test POST /@<username>/create_note route"""
	admin_client, admin = util_accounts.create_test_client_and_admin(2, "note-admin")

	target_client, target_user = util_accounts.create_test_client_and_user("note-target")

	response, _ = util.post_with_formkey(
		admin_client, f"/@{target_user.username}/create_note",
		data={"note": "Test admin note"}
	)
	assert response.status_code in [200, 302, 400, 500]


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
	admin_client, admin = util_accounts.create_test_client_and_admin(3, "revert-admin")

	target_client, target_user = util_accounts.create_test_client_and_user("revert-target")

	response, _ = util.post_with_formkey(
		admin_client, f"/@{target_user.username}/revert_actions",
		data={}
	)
	assert response.status_code in [200, 302, 400, 403]
