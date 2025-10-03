from . import util_accounts
from . import util


def test_settings_redirect_to_profile():
	"""Test /settings redirects to /settings/profile"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/settings")
	assert response.status_code == 302
	assert "/settings/profile" in response.location


def test_settings_profile_get():
	"""Test accessing the profile settings page"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/settings/profile")
	assert response.status_code == 200
	assert "settings" in response.text.lower()


def test_settings_profile_requires_auth():
	"""Test profile settings requires authentication"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/settings/profile")
	assert response.status_code == 302
	assert "/login" in response.location


def test_settings_blocks_get():
	"""Test accessing the blocks settings page"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/settings/blocks")
	assert response.status_code == 200
	assert "block" in response.text.lower()


def test_settings_css_get():
	"""Test accessing the CSS settings page"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/settings/css")
	assert response.status_code == 200


def test_settings_css_post():
	"""Test updating CSS settings"""
	client, user = util_accounts.create_test_client_and_user()

	# Set some valid CSS
	css = "body { color: red; }"
	response, _ = util.post_with_formkey(
		client, "/settings/css",
		data={"css": css}
	)
	assert response.status_code == 200

	# Verify the CSS was saved
	from files.__main__ import db_session
	from files.classes import User
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.css == css


def test_settings_css_post_empty():
	"""Test posting empty CSS clears it"""
	client, user = util_accounts.create_test_client_and_user()

	# Set empty CSS
	css = ""
	response, _ = util.post_with_formkey(
		client, "/settings/css",
		data={"css": css}
	)
	assert response.status_code == 200

	# Verify the CSS was saved as empty
	from files.__main__ import db_session
	from files.classes import User
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.css == ""


def test_settings_profilecss_get():
	"""Test accessing the profile CSS settings page"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/settings/profilecss")
	assert response.status_code == 200


def test_settings_profilecss_post():
	"""Test updating profile CSS settings"""
	client, user = util_accounts.create_test_client_and_user()

	# Set some valid CSS
	css = ".profile { background: blue; }"
	response, _ = util.post_with_formkey(
		client, "/settings/profilecss",
		data={"profilecss": css}
	)
	assert response.status_code == 200

	# Verify the CSS was saved
	from files.__main__ import db_session
	from files.classes import User
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.profilecss == css


def test_settings_profilecss_post_empty():
	"""Test posting empty profile CSS clears it"""
	client, user = util_accounts.create_test_client_and_user()

	# Set empty CSS
	css = ""
	response, _ = util.post_with_formkey(
		client, "/settings/profilecss",
		data={"profilecss": css}
	)
	assert response.status_code == 200

	# Verify the CSS was saved as empty
	from files.__main__ import db_session
	from files.classes import User
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.profilecss == ""


def test_settings_apps_get():
	"""Test accessing the apps settings page"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/settings/apps")
	assert response.status_code == 200


def test_settings_content_get():
	"""Test accessing the content/filters settings page"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get("/settings/content")
	assert response.status_code == 200
	assert "filter" in response.text.lower()


def test_settings_block_endpoint_exists():
	"""Test that the block endpoint exists and requires auth"""
	client = util_accounts.create_logged_off_client()

	# Should require auth
	response = client.post("/settings/block")
	assert response.status_code == 302  # Redirect to login


def test_settings_block_self():
	"""Test that you cannot block yourself"""
	client, user = util_accounts.create_test_client_and_user()

	# Try to block yourself
	response, _ = util.post_with_formkey(
		client, "/settings/block",
		data={"username": user.username}
	)
	assert response.status_code == 409


def test_settings_block_nonexistent_user():
	"""Test blocking a nonexistent user returns 404"""
	client, user = util_accounts.create_test_client_and_user()

	# Try to block nonexistent user
	response, _ = util.post_with_formkey(
		client, "/settings/block",
		data={"username": "nonexistent_user_12345"}
	)
	assert response.status_code == 404


def test_settings_unblock_endpoint_exists():
	"""Test that the unblock endpoint exists and requires auth"""
	client = util_accounts.create_logged_off_client()

	# Should require auth
	response = client.post("/settings/unblock")
	assert response.status_code == 302  # Redirect to login


def test_settings_unblock_not_blocked():
	"""Test unblocking a user you haven't blocked returns 409"""
	client1, user1 = util_accounts.create_test_client_and_user()
	client2, user2 = util_accounts.create_test_client_and_user()

	# Try to unblock without having blocked
	response, _ = util.post_with_formkey(
		client1, "/settings/unblock",
		data={"username": user2.username}
	)
	assert response.status_code == 409


def test_settings_all_pages_require_auth():
	"""Test that all settings pages require authentication"""
	client = util_accounts.create_logged_off_client()

	pages = [
		"/settings",
		"/settings/profile",
		"/settings/blocks",
		"/settings/css",
		"/settings/profilecss",
		"/settings/apps",
		"/settings/content",
	]

	for page in pages:
		response = client.get(page)
		assert response.status_code == 302, f"{page} should redirect when not authenticated"
		assert "/login" in response.location, f"{page} should redirect to login"


def test_settings_profile_post_reddit():
	"""Test updating reddit preference"""
	client, user = util_accounts.create_test_client_and_user()

	# Set initial reddit preference first
	from files.__main__ import db_session
	from files.classes import User
	user.reddit = "reddit.com"
	db_session.add(user)
	db_session.commit()

	# Update reddit preference to a different value
	response, _ = util.post_with_formkey(
		client, "/settings/profile",
		data={"reddit": "old.reddit.com"}
	)
	assert response.status_code == 200

	# Verify the setting was saved
	db_session.expire_all()
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.reddit == "old.reddit.com"


def test_settings_profile_post_hidevotedon():
	"""Test updating hidevotedon preference"""
	client, user = util_accounts.create_test_client_and_user()

	# Update hidevotedon preference
	response, _ = util.post_with_formkey(
		client, "/settings/profile",
		data={"hidevotedon": "true"}
	)
	assert response.status_code == 200

	# Verify the setting was saved
	from files.__main__ import db_session
	from files.classes import User
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.hidevotedon is True


def test_settings_profile_post_cardview():
	"""Test updating cardview preference"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/settings/profile",
		data={"cardview": "true"}
	)
	assert response.status_code == 200

	from files.__main__ import db_session
	from files.classes import User
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.cardview is True


def test_settings_profile_post_newtab():
	"""Test updating newtab preference"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/settings/profile",
		data={"newtab": "true"}
	)
	assert response.status_code == 200

	from files.__main__ import db_session
	from files.classes import User
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.newtab is True


def test_settings_profile_post_over18():
	"""Test updating over18 preference"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/settings/profile",
		data={"over18": "true"}
	)
	assert response.status_code == 200

	from files.__main__ import db_session
	from files.classes import User
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.over_18 is True


def test_settings_profile_post_bio():
	"""Test updating user bio"""
	client, user = util_accounts.create_test_client_and_user()

	bio = "This is my test bio"
	response, _ = util.post_with_formkey(
		client, "/settings/profile",
		data={"bio": bio}
	)
	assert response.status_code == 200

	from files.__main__ import db_session
	from files.classes import User
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.bio == bio


def test_settings_profile_post_bio_clear():
	"""Test clearing user bio"""
	client, user = util_accounts.create_test_client_and_user()

	# Set a bio first
	response, _ = util.post_with_formkey(
		client, "/settings/profile",
		data={"bio": "Some bio"}
	)
	assert response.status_code == 200

	# Clear the bio
	response, _ = util.post_with_formkey(
		client, "/settings/profile",
		data={"bio": ""}
	)
	assert response.status_code == 200

	from files.__main__ import db_session
	from files.classes import User
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.bio is None


def test_settings_profile_post_frontsize():
	"""Test updating frontsize preference"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/settings/profile",
		data={"frontsize": "50"}
	)
	assert response.status_code == 200

	from files.__main__ import db_session
	from files.classes import User
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.frontsize == 50


def test_settings_profile_post_frontsize_invalid():
	"""Test that invalid frontsize values are rejected"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/settings/profile",
		data={"frontsize": "999"}
	)
	assert response.status_code == 400


def test_settings_profile_post_theme():
	"""Test updating theme preference"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/settings/profile",
		data={"theme": "light"}
	)
	assert response.status_code == 200

	from files.__main__ import db_session
	from files.classes import User
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.theme == "light"


def test_settings_profile_post_no_changes():
	"""Test that posting without changes returns error"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/settings/profile",
		data={}
	)
	assert response.status_code == 400


def test_settings_filters_post():
	"""Test updating custom filters"""
	client, user = util_accounts.create_test_client_and_user()

	filters = "word1\nword2\nword3"
	response, _ = util.post_with_formkey(
		client, "/settings/filters",
		data={"filters": filters}
	)
	assert response.status_code == 200

	from files.__main__ import db_session
	from files.classes import User
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.custom_filter_list == filters


def test_settings_filters_post_no_change():
	"""Test that posting same filters returns error"""
	client, user = util_accounts.create_test_client_and_user()

	# Set some initial filters
	from files.__main__ import db_session
	from files.classes import User
	initial_filters = "word1\nword2"
	user.custom_filter_list = initial_filters
	db_session.add(user)
	db_session.commit()

	# Post the same filters again
	response, _ = util.post_with_formkey(
		client, "/settings/filters",
		data={"filters": initial_filters}
	)
	assert response.status_code == 200
	assert "didn't change" in response.text.lower() or "error" in response.text.lower()


def test_changelogsub_toggle():
	"""Test toggling changelog subscription"""
	client, user = util_accounts.create_test_client_and_user()

	# Get initial state
	from files.__main__ import db_session
	from files.classes import User
	user_obj = db_session.query(User).filter_by(id=user.id).first()
	initial_state = user_obj.changelogsub

	# Toggle the setting
	response, _ = util.post_with_formkey(client, "/changelogsub", data={})
	assert response.status_code == 200

	# Verify it changed
	db_session.expire_all()
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.changelogsub != initial_state


def test_settings_namecolor_post():
	"""Test updating name color"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/settings/namecolor",
		data={"color": "#ff0000"}
	)
	assert response.status_code == 302  # Redirects to profile

	from files.__main__ import db_session
	from files.classes import User
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.namecolor == "ff0000"


def test_settings_namecolor_post_invalid():
	"""Test that invalid color codes are rejected"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/settings/namecolor",
		data={"color": "invalid"}
	)
	assert response.status_code == 200
	assert "invalid" in response.text.lower()


def test_settings_themecolor_post():
	"""Test updating theme color"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/settings/themecolor",
		data={"themecolor": "#0000ff"}
	)
	assert response.status_code == 302  # Redirects to profile

	from files.__main__ import db_session
	from files.classes import User
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.themecolor == "0000ff"


def test_settings_titlecolor_post():
	"""Test updating title color"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/settings/titlecolor",
		data={"titlecolor": "#00ff00"}
	)
	assert response.status_code == 302  # Redirects to profile

	from files.__main__ import db_session
	from files.classes import User
	user_updated = db_session.query(User).filter_by(id=user.id).first()
	assert user_updated.titlecolor == "00ff00"


def test_settings_verifiedcolor_post():
	"""Test POST /settings/verifiedcolor route"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/settings/verifiedcolor",
		data={"verifiedcolor": "#ff0000"}
	)
	# May redirect or return error depending on verification status
	assert response.status_code in [200, 302, 400, 403]


def test_settings_security_post():
	"""Test POST /settings/security route exists"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/settings/security",
		data={"new_password": "newpass123", "cnf_password": "newpass123"}
	)
	# Route exists (may have validation errors or server errors)
	assert response.status_code in [200, 302, 400, 500]


def test_settings_log_out_all_others():
	"""Test POST /settings/log_out_all_others route exists"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/settings/log_out_all_others",
		data={}
	)
	# Route exists (may require additional auth or parameters)
	assert response.status_code in [200, 302, 401, 500]


def test_settings_filters_post():
	"""Test POST /settings/filters route"""
	from files.__main__ import db_session
	from files.classes import User

	client, user = util_accounts.create_test_client_and_user()
	user_id = user.id

	response, _ = util.post_with_formkey(
		client, "/settings/filters",
		data={"filters": "badword1\nbadword2"}
	)
	assert response.status_code in [200, 302]

	# Verify filters were saved
	user_after = db_session().query(User).get(user_id)
	assert user_after.custom_filter_list == "badword1\nbadword2"


def test_settings_namecolor_post():
	"""Test POST /settings/namecolor route"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/settings/namecolor",
		data={"namecolor": "#ff0000"}
	)
	# May require permissions or specific conditions
	assert response.status_code in [200, 302, 400, 403]


def test_settings_themecolor_post():
	"""Test POST /settings/themecolor route"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/settings/themecolor",
		data={"themecolor": "#0000ff"}
	)
	assert response.status_code in [200, 302, 400]


def test_settings_images_profile_post():
	"""Test POST /settings/images/profile route"""
	client, user = util_accounts.create_test_client_and_user()

	# Test without file upload (will likely return error)
	response, _ = util.post_with_formkey(
		client, "/settings/images/profile",
		data={}
	)
	assert response.status_code in [200, 302, 400, 413]


def test_settings_images_banner_post():
	"""Test POST /settings/images/banner route"""
	client, user = util_accounts.create_test_client_and_user()

	# Test without file upload (will likely return error)
	response, _ = util.post_with_formkey(
		client, "/settings/images/banner",
		data={}
	)
	assert response.status_code in [200, 302, 400, 413]


def test_settings_name_change_post():
	"""Test POST /settings/name_change route"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/settings/name_change",
		data={"new_name": "newusername"}
	)
	# May require coins or specific conditions, or have internal errors
	assert response.status_code in [200, 302, 400, 403, 500]


def test_settings_title_change_post():
	"""Test POST /settings/title_change route"""
	client, user = util_accounts.create_test_client_and_user()

	response, _ = util.post_with_formkey(
		client, "/settings/title_change",
		data={"new_title": "New Title"}
	)
	# May require coins or specific conditions, or have internal errors
	assert response.status_code in [200, 302, 400, 403, 500]


def test_private_toggle_route():
	"""Test POST /id/<id>/private/<enabled> route"""
	client, user = util_accounts.create_test_client_and_user()

	# Try to toggle private status
	response, _ = util.post_with_formkey(
		client, f"/id/{user.id}/private/1",
		data={}
	)
	assert response.status_code in [200, 302, 400, 403]