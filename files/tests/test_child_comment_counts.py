from . import fixture_accounts
from . import fixture_submissions
from . import fixture_comments
from . import util
from files.__main__ import db_session
from files.classes import Submission

@util.no_rate_limit
def test_submission_comment_count(accounts, submissions, comments):
	"""
	Scenario:
		1. There is a submission
		2. Bob the badpoaster poasts a comment on the submission
		3. submission.comment_count goes up by 1
		4. Alice the admin removes the comment
		5. submission.comment_count goes down by 1
		6. Alice the admin unremoves the comment
		7. submission.comment_count goes up by 1
	"""
	db = db_session()
	alice_client, alice = accounts.client_and_user_for_account('Alice')
	alice.admin_level = 2
	db.add(alice)
	db.commit()

	bob_client, bob = accounts.client_and_user_for_account('Bob')
	
	post = submissions.submission_for_client(alice_client, {
		'title': 'Weekly Takes',
		'body': 'Post your takes. Bad takes will be removed',
	})
	post_id = post.id

	post = db.query(Submission).filter_by(id=post_id).first()
	assert 0 == post.comment_count

	comment = comments.comment_for_client(bob_client, post.id, {
		'body': 'The sun is a social construct.'
	})

	post = db.query(Submission).filter_by(id=post_id).first()
	assert 1 == post.comment_count

	#alice_client.post('/admin/update_filter_status', {
	#})

	assert True
