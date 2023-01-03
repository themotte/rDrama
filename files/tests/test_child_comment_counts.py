from . import fixture_accounts
from . import fixture_submissions
from . import fixture_comments
from . import util
from files.__main__ import db_session
from files.classes import Submission
import json


def assert_comment_visibility(post, comment_body, clients):
	for client_name, (client, should_see) in clients.items():
		response = client.get(f'/post/{post.id}')
		if should_see:
			assert comment_body in response.text, f'{client_name} should see comment'
		else:
			assert comment_body not in response.text, f'{client_name} should not see comment'

@util.no_rate_limit
def test_submission_comment_count(accounts, submissions, comments):
	"""
	Scenario:
		1. There is a submission
		2. Bob the badpoaster poasts a comment on the submission
		3. submission.comment_count goes up by 1. Everyone can see the comment.
		4. Alice the admin removes the comment
		5. submission.comment_count goes down by 1. Only Bob and admins can see the comment.
	"""
	db = db_session()
	alice_client, alice = accounts.client_and_user_for_account('Alice')
	alice.admin_level = 2
	db.add(alice)
	db.commit()

	bob_client, bob = accounts.client_and_user_for_account('Bob')
	carol_client, carol = accounts.client_and_user_for_account('Carol')
	logged_off_client = accounts.logged_off()
	
	post = submissions.submission_for_client(alice_client, {
		'title': 'Weekly Takes',
		'body': 'Post your takes. Bad takes will be removed',
	})
	post_id = post.id

	post = db.query(Submission).filter_by(id=post_id).first()
	assert 0 == post.comment_count

	comment_body = 'The sun is a social construct.'
	comment = comments.comment_for_client(bob_client, post.id, {
		'body': comment_body,
	})

	post = db.query(Submission).filter_by(id=post_id).first()
	assert 1 == post.comment_count

	assert_comment_visibility(post, comment_body, {
		'alice': (alice_client, True),
		'bob': (bob_client, True),
		'carol': (carol_client, True),
		'guest': (logged_off_client, True),
	})

	alice_formkey = util.formkey_from(alice_client.get(f'/post/{post.id}').text)
	response = alice_client.post(
		'/admin/update_filter_status',
		data=json.dumps({
			'comment_id': comment.id,
			'new_status': 'removed',
			"formkey": alice_formkey,
		}),
		content_type='application/json'
	)
	assert 200 == response.status_code

	post = db.query(Submission).filter_by(id=post_id).first()

	assert_comment_visibility(post, comment_body, {
		# Alice should see the comment because she is an admin, level >= 2
		'alice': (alice_client, True),
		# Bob should see the comment because he wrote the comment
		'bob': (bob_client, True),
		# Other users, and guests, should NOT see the comment, since it has been removed
		'carol': (carol_client, False),
		'guest': (logged_off_client, False),
	})

	assert True
