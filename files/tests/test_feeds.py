from . import util_accounts
from . import util

@util.no_rate_limit
def test_rss_feed():
	"""Test that the RSS feed endpoint returns valid XML"""
	client = util_accounts.create_logged_off_client()
	response = client.get("/rss")
	assert response.status_code == 200
	assert response.headers['Content-Type'] == 'application/xml; charset=utf-8'
	assert response.text.startswith("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
	# Check for basic Atom feed structure
	assert 'xmlns="http://www.w3.org/2005/Atom"' in response.text
	assert '<title type="text">' in response.text

def test_feed_alias():
	"""Test that the /feed endpoint is an alias for /rss"""
	client = util_accounts.create_logged_off_client()
	response = client.get("/feed")
	assert response.status_code == 200
	assert response.headers['Content-Type'] == 'application/xml; charset=utf-8'
	assert response.text.startswith("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")

def test_rss_feed_with_sort_and_time():
	"""Test RSS feed with sort and time parameters"""
	client = util_accounts.create_logged_off_client()
	response = client.get("/rss/new/day")
	assert response.status_code == 200
	assert response.headers['Content-Type'] == 'application/xml; charset=utf-8'
	assert response.text.startswith("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
	assert 'xmlns="http://www.w3.org/2005/Atom"' in response.text

@util.no_rate_limit
def test_rss_feed_contains_new_post():
	"""Test that a newly created post appears in the RSS feed"""
	client, user = util_accounts.create_test_client_and_user()

	# Create a unique post
	post_title = f"RSS Test Post {util.generate_text()}"
	post_body = f"RSS Test Body {util.generate_text()}"

	# Submit the post
	submit_post_response, submit_get_response = util.post_with_formkey(
		client, "/submit", "/submit",
		data={
			"title": post_title,
			"body": post_body,
		}
	)

	assert submit_post_response.status_code == 200

	# Check that the post appears in the RSS feed
	rss_response = client.get("/rss")
	assert rss_response.status_code == 200
	assert post_title in rss_response.text

	# Also verify it appears in the parameterized feed
	rss_new_response = client.get("/rss/new/all")
	assert rss_new_response.status_code == 200
	assert post_title in rss_new_response.text