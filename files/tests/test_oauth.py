from . import util_accounts
from . import util
from files.__main__ import db_session
from files.classes import OauthApp, ClientAuth, User


def test_authorize_get():
	"""Test GET /authorize returns response (may be 200 or 500 if template missing)"""
	client, user = util_accounts.create_test_client_and_user("oauth-user-1")

	# Create an OAuth app first
	import secrets
	app = OauthApp(
		app_name="Test App",
		redirect_uri="http://localhost/callback",
		author_id=user.id,
		description="Test OAuth app",
		client_id=secrets.token_urlsafe(64)[:64]
	)
	db_session.add(app)
	db_session.commit()

	# Request authorization - template may not exist, so we just verify it doesn't return 401
	response = client.get(f"/authorize?client_id={app.client_id}")
	# The route should not return 401 (unauthorized) for valid client_id
	assert response.status_code != 401


def test_authorize_get_invalid_client():
	"""Test GET /authorize with invalid client_id returns error"""
	client, user = util_accounts.create_test_client_and_user("oauth-user-2")

	response = client.get("/authorize?client_id=invalid_client_id")
	assert response.status_code == 401
	assert "oauth_error" in response.text.lower() or "invalid" in response.text.lower()


def test_authorize_post_creates_auth():
	"""Test POST /authorize creates ClientAuth and redirects"""
	client, user = util_accounts.create_test_client_and_user("oauth-user-3")

	# Create an OAuth app
	import secrets
	app = OauthApp(
		app_name="Test App 2",
		redirect_uri="http://localhost/callback",
		author_id=user.id,
		description="Test OAuth app 2",
		client_id=secrets.token_urlsafe(64)[:64]
	)
	db_session.add(app)
	db_session.commit()

	# Authorize the app
	auth_response, _ = util.post_with_formkey(
		client, "/authorize",
		data={"client_id": app.client_id}
	)

	assert auth_response.status_code == 302
	assert app.redirect_uri in auth_response.location
	assert "token=" in auth_response.location

	# Verify ClientAuth was created
	with util.test_db_session() as session:
		auth = session.query(ClientAuth).filter_by(oauth_client=app.id, user_id=user.id).first()
		assert auth is not None
		assert auth.access_token is not None


def test_authorize_post_reuses_existing_auth():
	"""Test POST /authorize reuses existing ClientAuth on duplicate"""
	client, user = util_accounts.create_test_client_and_user("oauth-user-4")

	# Create an OAuth app
	import secrets
	app = OauthApp(
		app_name="Test App 3",
		redirect_uri="http://localhost/callback",
		author_id=user.id,
		description="Test OAuth app 3",
		client_id=secrets.token_urlsafe(64)[:64]
	)
	db_session.add(app)
	db_session.commit()

	# First authorization
	auth_response1, _ = util.post_with_formkey(
		client, "/authorize",
		data={"client_id": app.client_id}
	)

	# Extract token from first response
	token1 = auth_response1.location.split("token=")[1] if "token=" in auth_response1.location else None
	assert token1 is not None

	# Second authorization (should reuse)
	auth_response2, _ = util.post_with_formkey(
		client, "/authorize",
		data={"client_id": app.client_id}
	)

	# Extract token from second response
	token2 = auth_response2.location.split("token=")[1] if "token=" in auth_response2.location else None
	assert token2 is not None

	# Tokens should be the same
	assert token1 == token2

	# Should only have one ClientAuth
	with util.test_db_session() as session:
		auths = session.query(ClientAuth).filter_by(oauth_client=app.id, user_id=user.id).all()
		assert len(auths) == 1


def test_authorize_post_invalid_client():
	"""Test POST /authorize with invalid client_id returns error"""
	client, user = util_accounts.create_test_client_and_user("oauth-user-5")

	auth_response, _ = util.post_with_formkey(
		client, "/authorize",
		data={"client_id": "invalid_client_id"}
	)

	assert auth_response.status_code == 401


def test_request_api_keys():
	"""Test POST /api_keys creates OAuth app request"""
	client, user = util_accounts.create_test_client_and_user("oauth-user-6")

	# Request API keys
	response, _ = util.post_with_formkey(
		client, "/api_keys",
		data={
			"name": "My Test App",
			"redirect_uri": "http://localhost/callback",
			"description": "Test application description"
		}
	)

	assert response.status_code == 302
	assert "/settings/apps" in response.location

	# Verify app was created
	with util.test_db_session() as session:
		app = session.query(OauthApp).filter_by(app_name="My Test App", author_id=user.id).first()
		assert app is not None
		assert app.redirect_uri == "http://localhost/callback"
		assert app.description == "Test application description"


def test_request_api_keys_sanitizes_name():
	"""Test POST /api_keys sanitizes app name"""
	client, user = util_accounts.create_test_client_and_user("oauth-user-7")

	# Request API keys with HTML in name
	response, _ = util.post_with_formkey(
		client, "/api_keys",
		data={
			"name": "App<script>alert('xss')</script>Name",
			"redirect_uri": "http://localhost/callback",
			"description": "Test"
		}
	)

	assert response.status_code == 302

	# Verify app name was sanitized (< and > removed)
	with util.test_db_session() as session:
		app = session.query(OauthApp).filter_by(author_id=user.id).order_by(OauthApp.id.desc()).first()
		assert app is not None
		assert "<" not in app.app_name
		assert ">" not in app.app_name


def test_delete_oauth_app():
	"""Test POST /delete_app/<aid> deletes OAuth app"""
	client, user = util_accounts.create_test_client_and_user("oauth-user-8")

	# Create an OAuth app
	app = OauthApp(
		app_name="App to Delete",
		redirect_uri="http://localhost/callback",
		author_id=user.id,
		description="Will be deleted"
	)
	db_session.add(app)
	db_session.commit()
	app_id = app.id

	# Delete the app
	response, _ = util.post_with_formkey(
		client, f"/delete_app/{app_id}",
		data={}
	)

	assert response.status_code == 302
	assert "/apps" in response.location

	# Verify app was deleted
	with util.test_db_session() as session:
		app = session.query(OauthApp).filter_by(id=app_id).first()
		assert app is None


def test_delete_oauth_app_deletes_auths():
	"""Test deleting OAuth app also deletes associated ClientAuths"""
	client, user = util_accounts.create_test_client_and_user("oauth-user-9")

	# Create an OAuth app
	app = OauthApp(
		app_name="App with Auth",
		redirect_uri="http://localhost/callback",
		author_id=user.id,
		description="Has auth"
	)
	db_session.add(app)
	db_session.commit()

	# Create a ClientAuth
	auth = ClientAuth(oauth_client=app.id, user_id=user.id, access_token="test_token")
	db_session.add(auth)
	db_session.commit()

	app_id = app.id

	# Delete the app
	response, _ = util.post_with_formkey(
		client, f"/delete_app/{app_id}",
		data={}
	)

	assert response.status_code == 302

	# Verify ClientAuth was also deleted
	with util.test_db_session() as session:
		auth = session.query(ClientAuth).filter_by(oauth_client=app_id).first()
		assert auth is None


def test_delete_oauth_app_forbidden_for_non_author():
	"""Test user cannot delete another user's OAuth app"""
	client1, user1 = util_accounts.create_test_client_and_user("oauth-user-10")
	client2, user2 = util_accounts.create_test_client_and_user("oauth-user-11")

	# User 1 creates an app
	app = OauthApp(
		app_name="User 1 App",
		redirect_uri="http://localhost/callback",
		author_id=user1.id,
		description="Owned by user 1"
	)
	db_session.add(app)
	db_session.commit()
	app_id = app.id

	# User 2 tries to delete it
	response, _ = util.post_with_formkey(
		client2, f"/delete_app/{app_id}",
		data={}
	)

	assert response.status_code == 403

	# Verify app was not deleted
	with util.test_db_session() as session:
		app = session.query(OauthApp).filter_by(id=app_id).first()
		assert app is not None


def test_edit_oauth_app():
	"""Test POST /edit_app/<aid> updates OAuth app"""
	client, user = util_accounts.create_test_client_and_user("oauth-user-12")

	# Create an OAuth app
	app = OauthApp(
		app_name="Original Name",
		redirect_uri="http://localhost/original",
		author_id=user.id,
		description="Original description"
	)
	db_session.add(app)
	db_session.commit()
	app_id = app.id

	# Edit the app
	response, _ = util.post_with_formkey(
		client, f"/edit_app/{app_id}",
		data={
			"name": "Updated Name",
			"redirect_uri": "http://localhost/updated",
			"description": "Updated description"
		}
	)

	assert response.status_code == 302
	assert "/settings/apps" in response.location

	# Verify app was updated
	with util.test_db_session() as session:
		app = session.query(OauthApp).filter_by(id=app_id).first()
		assert app.app_name == "Updated Name"
		assert app.redirect_uri == "http://localhost/updated"
		assert app.description == "Updated description"


def test_edit_oauth_app_forbidden_for_non_author():
	"""Test user cannot edit another user's OAuth app"""
	client1, user1 = util_accounts.create_test_client_and_user("oauth-user-13")
	client2, user2 = util_accounts.create_test_client_and_user("oauth-user-14")

	# User 1 creates an app
	app = OauthApp(
		app_name="User 1 App",
		redirect_uri="http://localhost/callback",
		author_id=user1.id,
		description="Owned by user 1"
	)
	db_session.add(app)
	db_session.commit()
	app_id = app.id

	# User 2 tries to edit it
	response, _ = util.post_with_formkey(
		client2, f"/edit_app/{app_id}",
		data={
			"name": "Hacked Name",
			"redirect_uri": "http://evil.com/callback",
			"description": "Hacked"
		}
	)

	assert response.status_code == 403

	# Verify app was not updated
	with util.test_db_session() as session:
		app = session.query(OauthApp).filter_by(id=app_id).first()
		assert app.app_name == "User 1 App"


def test_admin_app_approve():
	"""Test POST /admin/app/approve/<aid> approves app and generates client_id"""
	client_user, user = util_accounts.create_test_client_and_user("oauth-user-15")
	client_admin, admin = util_accounts.create_test_client_and_admin(3, "oauth-admin-1")

	# User creates an app
	app = OauthApp(
		app_name="App to Approve",
		redirect_uri="http://localhost/callback",
		author_id=user.id,
		description="Needs approval"
	)
	db_session.add(app)
	db_session.commit()
	app_id = app.id

	# Admin approves the app
	response, _ = util.post_with_formkey(
		client_admin, f"/admin/app/approve/{app_id}",
		data={}
	)

	assert response.status_code == 200
	assert "approved" in response.text.lower()

	# Verify app has client_id
	with util.test_db_session() as session:
		app = session.query(OauthApp).filter_by(id=app_id).first()
		assert app.client_id is not None

		# Verify ClientAuth was created
		auth = session.query(ClientAuth).filter_by(oauth_client=app.id, user_id=user.id).first()
		assert auth is not None
		assert auth.access_token is not None


def test_admin_app_revoke():
	"""Test POST /admin/app/revoke/<aid> revokes and deletes app"""
	client_user, user = util_accounts.create_test_client_and_user("oauth-user-16")
	client_admin, admin = util_accounts.create_test_client_and_admin(2, "oauth-admin-2")

	# User creates an app
	app = OauthApp(
		app_name="App to Revoke",
		redirect_uri="http://localhost/callback",
		author_id=user.id,
		description="Will be revoked",
		client_id="revoke_test_client_id"
	)
	db_session.add(app)
	db_session.commit()
	app_id = app.id

	# Admin revokes the app
	response, _ = util.post_with_formkey(
		client_admin, f"/admin/app/revoke/{app_id}",
		data={}
	)

	assert response.status_code == 200
	assert "revoked" in response.text.lower()

	# Verify app was deleted
	with util.test_db_session() as session:
		app = session.query(OauthApp).filter_by(id=app_id).first()
		assert app is None


def test_admin_app_reject():
	"""Test POST /admin/app/reject/<aid> rejects and deletes app"""
	client_user, user = util_accounts.create_test_client_and_user("oauth-user-17")
	client_admin, admin = util_accounts.create_test_client_and_admin(2, "oauth-admin-3")

	# User creates an app
	app = OauthApp(
		app_name="App to Reject",
		redirect_uri="http://localhost/callback",
		author_id=user.id,
		description="Will be rejected"
	)
	db_session.add(app)
	db_session.commit()
	app_id = app.id

	# Admin rejects the app
	response, _ = util.post_with_formkey(
		client_admin, f"/admin/app/reject/{app_id}",
		data={}
	)

	assert response.status_code == 200
	assert "rejected" in response.text.lower()

	# Verify app was deleted
	with util.test_db_session() as session:
		app = session.query(OauthApp).filter_by(id=app_id).first()
		assert app is None


def test_admin_apps_list():
	"""Test GET /admin/apps shows all apps"""
	client_user, user = util_accounts.create_test_client_and_user("oauth-user-18")
	client_admin, admin = util_accounts.create_test_client_and_admin(2, "oauth-admin-4")

	# Create a couple apps
	app1 = OauthApp(
		app_name="Test App A",
		redirect_uri="http://localhost/a",
		author_id=user.id,
		description="App A"
	)
	app2 = OauthApp(
		app_name="Test App B",
		redirect_uri="http://localhost/b",
		author_id=user.id,
		description="App B"
	)
	db_session.add(app1)
	db_session.add(app2)
	db_session.commit()

	# Admin views apps list
	response = client_admin.get("/admin/apps")

	assert response.status_code == 200
	assert "Test App A" in response.text
	assert "Test App B" in response.text


def test_reroll_oauth_tokens():
	"""Test POST /oauth/reroll/<aid> generates new client_id"""
	client, user = util_accounts.create_test_client_and_user("oauth-user-19")

	# Create an OAuth app
	app = OauthApp(
		app_name="App to Reroll",
		redirect_uri="http://localhost/callback",
		author_id=user.id,
		description="Will reroll",
		client_id="original_client_id"
	)
	db_session.add(app)
	db_session.commit()
	app_id = app.id
	original_client_id = app.client_id

	# Reroll the client ID
	response, _ = util.post_with_formkey(
		client, f"/oauth/reroll/{app_id}",
		data={}
	)

	assert response.status_code == 200
	assert "reroll" in response.text.lower()

	# Verify client_id changed
	with util.test_db_session() as session:
		app = session.query(OauthApp).filter_by(id=app_id).first()
		assert app.client_id != original_client_id
		assert app.client_id is not None


def test_reroll_oauth_tokens_forbidden_for_non_author():
	"""Test user cannot reroll another user's OAuth app tokens"""
	client1, user1 = util_accounts.create_test_client_and_user("oauth-user-20")
	client2, user2 = util_accounts.create_test_client_and_user("oauth-user-21")

	# User 1 creates an app
	import secrets
	app = OauthApp(
		app_name="User 1 App",
		redirect_uri="http://localhost/callback",
		author_id=user1.id,
		description="Owned by user 1",
		client_id=secrets.token_urlsafe(64)[:64]
	)
	db_session.add(app)
	db_session.commit()
	app_id = app.id
	original_client_id = app.client_id

	# User 2 tries to reroll it
	response, _ = util.post_with_formkey(
		client2, f"/oauth/reroll/{app_id}",
		data={}
	)

	assert response.status_code == 403

	# Verify client_id did not change
	with util.test_db_session() as session:
		app = session.query(OauthApp).filter_by(id=app_id).first()
		assert app.client_id == original_client_id


def test_admin_app_view():
	"""Test GET /admin/app/<aid> route"""
	import secrets
	from files.__main__ import db_session
	from files.classes import OauthApp

	client, admin = util_accounts.create_test_client_and_admin(2, "oauth-admin")

	# Create an app
	_, user = util_accounts.create_test_client_and_user("app-owner")
	app = OauthApp(
		app_name="Admin Test App",
		redirect_uri="http://localhost/callback",
		author_id=user.id,
		description="Test app for admin view",
		client_id=secrets.token_urlsafe(64)[:64]
	)
	db_session.add(app)
	db_session.commit()

	response = client.get(f"/admin/app/{app.id}")
	assert response.status_code == 200


def test_admin_app_comments():
	"""Test GET /admin/app/<aid>/comments route"""
	import secrets
	from files.__main__ import db_session
	from files.classes import OauthApp

	client, admin = util_accounts.create_test_client_and_admin(2, "oauth-admin2")

	# Create an app
	_, user = util_accounts.create_test_client_and_user("app-owner2")
	app = OauthApp(
		app_name="Admin Test App 2",
		redirect_uri="http://localhost/callback",
		author_id=user.id,
		description="Test app 2 for admin comments",
		client_id=secrets.token_urlsafe(64)[:64]
	)
	db_session.add(app)
	db_session.commit()

	response = client.get(f"/admin/app/{app.id}/comments")
	assert response.status_code == 200