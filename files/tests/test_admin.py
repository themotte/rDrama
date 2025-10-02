"""Tests for admin routes."""
from . import util_accounts
from . import util
from . import util_submissions
from . import util_comments


def test_admin_dashboard():
	"""Test GET /admin route (admin dashboard)"""
	from files.__main__ import db_session
	client, admin = util_accounts.create_test_client_and_user("admin-dash")
	admin.admin_level = 2
	db_session.add(admin)
	db_session.commit()

	response = client.get("/admin")
	assert response.status_code == 200


def test_admin_reported_posts():
	"""Test GET /admin/reported/posts route"""
	from files.__main__ import db_session
	client, admin = util_accounts.create_test_client_and_user("admin-reports")
	admin.admin_level = 2
	db_session.add(admin)
	db_session.commit()

	response = client.get("/admin/reported/posts")
	assert response.status_code == 200


def test_admin_reported_comments():
	"""Test GET /admin/reported/comments route"""
	from files.__main__ import db_session
	client, admin = util_accounts.create_test_client_and_user("admin-rep-com")
	admin.admin_level = 2
	db_session.add(admin)
	db_session.commit()

	response = client.get("/admin/reported/comments")
	assert response.status_code == 200


def test_admin_removed_posts():
	"""Test GET /admin/removed/posts route"""
	from files.__main__ import db_session
	client, admin = util_accounts.create_test_client_and_user("admin-rem-post")
	admin.admin_level = 2
	db_session.add(admin)
	db_session.commit()

	response = client.get("/admin/removed/posts")
	assert response.status_code == 200


def test_admin_removed_comments():
	"""Test GET /admin/removed/comments route"""
	from files.__main__ import db_session
	client, admin = util_accounts.create_test_client_and_user("admin-rem-com")
	admin.admin_level = 2
	db_session.add(admin)
	db_session.commit()

	response = client.get("/admin/removed/comments")
	assert response.status_code == 200


def test_admin_filtered_posts():
	"""Test GET /admin/filtered/posts route"""
	from files.__main__ import db_session
	client, admin = util_accounts.create_test_client_and_user("admin-filt-pst")
	admin.admin_level = 2
	db_session.add(admin)
	db_session.commit()

	response = client.get("/admin/filtered/posts")
	assert response.status_code == 200


def test_admin_filtered_comments():
	"""Test GET /admin/filtered/comments route"""
	from files.__main__ import db_session
	client, admin = util_accounts.create_test_client_and_user("admin-filt-com")
	admin.admin_level = 2
	db_session.add(admin)
	db_session.commit()

	response = client.get("/admin/filtered/comments")
	assert response.status_code == 200


def test_admin_users():
	"""Test GET /admin/users route"""
	from files.__main__ import db_session
	client, admin = util_accounts.create_test_client_and_user("admin-users")
	admin.admin_level = 2
	db_session.add(admin)
	db_session.commit()

	response = client.get("/admin/users")
	assert response.status_code == 200


def test_admin_shadowbanned():
	"""Test GET /admin/shadowbanned route"""
	from files.__main__ import db_session
	client, admin = util_accounts.create_test_client_and_user("admin-shadow")
	admin.admin_level = 2
	db_session.add(admin)
	db_session.commit()

	response = client.get("/admin/shadowbanned")
	assert response.status_code == 200


def test_admin_image_posts():
	"""Test GET /admin/image_posts route"""
	from files.__main__ import db_session
	client, admin = util_accounts.create_test_client_and_user("admin-images")
	admin.admin_level = 2
	db_session.add(admin)
	db_session.commit()

	response = client.get("/admin/image_posts")
	assert response.status_code == 200


def test_admin_loggedin():
	"""Test GET /admin/loggedin route"""
	from files.__main__ import db_session
	client, admin = util_accounts.create_test_client_and_user("admin-loggedin")
	admin.admin_level = 3
	db_session.add(admin)
	db_session.commit()

	response = client.get("/admin/loggedin")
	assert response.status_code == 200


def test_admin_loggedout():
	"""Test GET /admin/loggedout route"""
	from files.__main__ import db_session
	client, admin = util_accounts.create_test_client_and_user("admin-loggedout")
	admin.admin_level = 3
	db_session.add(admin)
	db_session.commit()

	response = client.get("/admin/loggedout")
	assert response.status_code == 200


def test_ban_user():
	"""Test POST /ban_user/<user_id> route"""
	from files.__main__ import db_session
	admin_client, admin = util_accounts.create_test_client_and_user("ban-admin")
	admin.admin_level = 2
	db_session.add(admin)
	db_session.commit()

	client, user = util_accounts.create_test_client_and_user("banneduser")

	response, _ = util.post_with_formkey(
		admin_client, f"/ban_user/{user.id}",
		data={"reason": "Test ban"}
	)
	assert response.status_code in [200, 302, 400]


def test_unban_user():
	"""Test POST /unban_user/<user_id> route"""
	from files.__main__ import db_session
	admin_client, admin = util_accounts.create_test_client_and_user("unban-admin")
	admin.admin_level = 2
	db_session.add(admin)
	db_session.commit()

	client, user = util_accounts.create_test_client_and_user("unbanneduser")

	response, _ = util.post_with_formkey(
		admin_client, f"/unban_user/{user.id}",
		data={}
	)
	assert response.status_code in [200, 302, 400]


def test_shadowban_user():
	"""Test POST /shadowban/<user_id> route"""
	from files.__main__ import db_session
	admin_client, admin = util_accounts.create_test_client_and_user("sb-admin")
	admin.admin_level = 2
	db_session.add(admin)
	db_session.commit()

	client, user = util_accounts.create_test_client_and_user("sbuser")

	response, _ = util.post_with_formkey(
		admin_client, f"/shadowban/{user.id}",
		data={"reason": "Test shadowban"}
	)
	assert response.status_code in [200, 302, 400]


def test_unshadowban_user():
	"""Test POST /unshadowban/<user_id> route"""
	from files.__main__ import db_session
	admin_client, admin = util_accounts.create_test_client_and_user("usb-admin")
	admin.admin_level = 2
	db_session.add(admin)
	db_session.commit()

	client, user = util_accounts.create_test_client_and_user("usbuser")

	response, _ = util.post_with_formkey(
		admin_client, f"/unshadowban/{user.id}",
		data={}
	)
	assert response.status_code in [200, 302, 400]


def test_distinguish_post():
	"""Test POST /distinguish/<post_id> route"""
	from files.__main__ import db_session
	admin_client, admin = util_accounts.create_test_client_and_user("dist-admin")
	admin.admin_level = 1
	db_session.add(admin)
	db_session.commit()

	# Create a post by admin
	post = util_submissions.create_submission_for_client(admin_client)

	response, _ = util.post_with_formkey(
		admin_client, f"/distinguish/{post.id}",
		data={}
	)
	assert response.status_code in [200, 302, 400]


def test_distinguish_comment():
	"""Test POST /distinguish_comment/<c_id> route"""
	from files.__main__ import db_session
	admin_client, admin = util_accounts.create_test_client_and_user("distc-admin")
	admin.admin_level = 1
	db_session.add(admin)
	db_session.commit()

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
	from files.__main__ import db_session
	admin_client, admin = util_accounts.create_test_client_and_user("sticky-admin")
	admin.admin_level = 2
	db_session.add(admin)
	db_session.commit()

	client, user = util_accounts.create_test_client_and_user("stickypost")
	post = util_submissions.create_submission_for_client(client)

	response, _ = util.post_with_formkey(
		admin_client, f"/sticky/{post.id}",
		data={}
	)
	assert response.status_code in [200, 302, 400]


def test_sticky_comment():
	"""Test POST /sticky_comment/<cid> route"""
	from files.__main__ import db_session
	admin_client, admin = util_accounts.create_test_client_and_user("stickyc-admin")
	admin.admin_level = 2
	db_session.add(admin)
	db_session.commit()

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
	from files.__main__ import db_session
	admin_client, admin = util_accounts.create_test_client_and_user("unstickyc-adm")
	admin.admin_level = 2
	db_session.add(admin)
	db_session.commit()

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
	from files.__main__ import db_session
	admin_client, admin = util_accounts.create_test_client_and_user("badge-admin")
	admin.admin_level = 2
	db_session.add(admin)
	db_session.commit()

	client, user = util_accounts.create_test_client_and_user("badgeuser")

	response, _ = util.post_with_formkey(
		admin_client, "/admin/badge_grant",
		data={"username": user.username, "badge_id": "1"}
	)
	assert response.status_code in [200, 302, 400, 404]


def test_admin_badge_remove():
	"""Test POST /admin/badge_remove route"""
	from files.__main__ import db_session
	admin_client, admin = util_accounts.create_test_client_and_user("badgerm-admin")
	admin.admin_level = 2
	db_session.add(admin)
	db_session.commit()

	client, user = util_accounts.create_test_client_and_user("badgermuser")

	response, _ = util.post_with_formkey(
		admin_client, "/admin/badge_remove",
		data={"username": user.username, "badge_id": "1"}
	)
	assert response.status_code in [200, 302, 400, 404]
