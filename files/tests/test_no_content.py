from . import fixture_accounts
from . import util

@util.no_rate_limit
def test_no_content_submissions(accounts):
	client = accounts.client_for_account()

	# get our formkey
	submit_get_response = client.get("/submit")
	assert submit_get_response.status_code == 200

	title = '\u200e\u200e\u200e\u200e\u200e\u200e'
	body = util.generate_text()
	formkey = util.formkey_from(submit_get_response.text)

	# test bad title against good content
	submit_post_response = client.post("/submit", data={
		"title": title,
		"body": body,
		"formkey": formkey,
	})

	assert submit_post_response.status_code == 400

	title, body = body, title
	# test good title against bad content
	submit_post_response = client.post("/submit", data={
		"title": title,
		"body": body,
		"formkey": formkey,
	})

	assert submit_post_response.status_code == 400

@util.no_rate_limit
def test_no_content_comments(accounts):
	client = accounts.client_for_account()

	# get our formkey
	submit_get_response = client.get("/submit")
	assert submit_get_response.status_code == 200

	# make the post
	post_title = util.generate_text()
	post_body = util.generate_text()
	submit_post_response = client.post("/submit", data={
		"title": post_title,
		"body": post_body,
		"formkey": util.formkey_from(submit_get_response.text),
	})

	assert submit_post_response.status_code == 200
	assert post_title in submit_post_response.text
	assert post_body in submit_post_response.text

	# verify it actually got posted
	root_response = client.get("/")
	assert root_response.status_code == 200
	assert post_title in root_response.text
	assert post_body in root_response.text

	# yank the ID out
	post = util.ItemData.from_html(submit_post_response.text)
	
	# post a comment child
	comment_body = '\ufeff\ufeff\ufeff\ufeff\ufeff'
	submit_comment_response = client.post("/comment", data={
		"parent_fullname": post.id_full,
		"parent_level": 1,
		"submission": post.id,
		"body": comment_body,
		"formkey": util.formkey_from(submit_post_response.text),
	})
	assert submit_comment_response.status_code == 400
