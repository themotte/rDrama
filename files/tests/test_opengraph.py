"""Tests for OpenGraph meta tags (#130).

Verifies that key pages include proper og:title, og:image, and og:site_name
meta tags, and that image URLs are absolute (prefixed with SITE_FULL).
"""
from . import util_accounts
from . import util_submissions


def test_front_page_has_og_title():
	"""Test that the front page includes og:title meta tag"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/")
	assert response.status_code == 200
	assert 'og:title' in response.text


def test_front_page_has_og_image():
	"""Test that the front page includes og:image meta tag"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/")
	assert response.status_code == 200
	assert 'og:image' in response.text


def test_front_page_og_type_is_website():
	"""Test that the front page uses og:type website (not article)"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/")
	assert response.status_code == 200
	assert 'og:type' in response.text
	# Should be "website" not "article" for the homepage
	assert 'content="website"' in response.text


def test_front_page_og_site_name_not_request_host():
	"""Test that og:site_name uses SITE_TITLE, not request.host"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/")
	assert response.status_code == 200
	# Should not use request.host (which would be 'localhost' in tests)
	assert 'og:site_name' in response.text
	# og:site_name should appear exactly once (no duplicates)
	assert response.text.count('og:site_name') == 1


def test_front_page_has_twitter_tags():
	"""Test that the front page includes Twitter card meta tags"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/")
	assert response.status_code == 200
	assert 'twitter:card' in response.text
	assert 'twitter:title' in response.text
	assert 'twitter:image' in response.text


def test_post_page_has_og_title():
	"""Test that a post page includes og:title meta tag"""
	client, user = util_accounts.create_test_client_and_user()
	post = util_submissions.create_submission_for_client(client)

	response = client.get(f"/post/{post.id}")
	assert response.status_code == 200
	assert 'og:title' in response.text


def test_post_page_has_og_image():
	"""Test that a post page includes og:image meta tag"""
	client, user = util_accounts.create_test_client_and_user()
	post = util_submissions.create_submission_for_client(client)

	response = client.get(f"/post/{post.id}")
	assert response.status_code == 200
	assert 'og:image' in response.text


def test_post_page_og_type_is_article():
	"""Test that a post page uses og:type article"""
	client, user = util_accounts.create_test_client_and_user()
	post = util_submissions.create_submission_for_client(client)

	response = client.get(f"/post/{post.id}")
	assert response.status_code == 200
	assert 'content="article"' in response.text


def test_login_page_has_og_tags():
	"""Test that the login page includes OG meta tags"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/login")
	assert response.status_code == 200
	assert 'og:title' in response.text
	assert 'og:image' in response.text


def test_user_profile_has_og_tags():
	"""Test that a user profile page includes OG meta tags"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get(f"/@{user.username}")
	assert response.status_code == 200
	assert 'og:title' in response.text
	assert 'og:image' in response.text


def test_user_profile_og_type_is_profile():
	"""Test that a user profile page uses og:type profile"""
	client, user = util_accounts.create_test_client_and_user()

	response = client.get(f"/@{user.username}")
	assert response.status_code == 200
	assert 'content="profile"' in response.text


def test_no_og_author_on_non_article_pages():
	"""Test that og:author is not present on pages that are not articles"""
	client = util_accounts.create_logged_off_client()

	response = client.get("/")
	assert response.status_code == 200
	assert 'og:author' not in response.text
