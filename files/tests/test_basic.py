
from . import fixture_accounts
from . import util

def test_rules(accounts):
	response = accounts.logged_off().get("/rules")
	assert response.status_code == 200
	assert response.text.startswith("<!DOCTYPE html>")

@util.no_rate_limit
def test_post_and_comment(accounts):
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
	comment_body = util.generate_text()
	submit_comment_response = client.post("/comment", data={
		"parent_fullname": post.id_full,
		"parent_level": 1,
		"submission": post.id,
		"body": comment_body,
		"formkey": util.formkey_from(submit_post_response.text),
	})
	assert submit_comment_response.status_code == 200

	# verify it actually got posted
	post_response = client.get(post.url)
	assert post_response.status_code == 200
	assert comment_body in post_response.text

	# yank the ID out again
	comment = util.ItemData.from_json(submit_comment_response.text)

	# post a comment grandchild!
	grandcomment_body = util.generate_text()
	submit_grandcomment_response = client.post("/comment", data={
		"parent_fullname": comment.id_full,
		"parent_level": 1,
		"submission": comment.id,
		"body": grandcomment_body,
		"formkey": util.formkey_from(submit_post_response.text),
	})
	assert submit_grandcomment_response.status_code == 200

	# verify it actually got posted
	post_response = client.get(post.url)
	assert post_response.status_code == 200
	assert grandcomment_body in post_response.text
