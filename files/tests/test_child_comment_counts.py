from . import fixture_accounts
from . import fixture_submissions
from . import fixture_comments
from . import util
from flask import g
from files.__main__ import app, db_session
from files.classes import Submission, Comment, User
from files.helpers.comments import bulk_recompute_descendant_counts
import json
import random


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

	assert 0 == post.comment_count

@util.no_rate_limit
def test_comment_descendant_count(accounts, submissions, comments):
	"""
		Here is a contentious top-level comment
			You're wrong, this isn't contentious
				no u
			Good poast
	"""
	db = db_session()
	alice_client, alice = accounts.client_and_user_for_account('Alice')

	post = submissions.submission_for_client(alice_client, {
		'title': 'Discussion',
		'body': 'Discuss stuff',
	})
	post_id = post.id

	root = comments.comment_for_client(alice_client, post.id, {
		'body': 'Here is a contentious top-level comment',
	})

	assert 0 == db.query(Comment).filter_by(id=root.id).first().descendant_count

	reply1 = comments.comment_for_client(alice_client, post.id, {
		'body': 'You\'re wrong, this isn\'t contentious',
		'parent_fullname': f't3_{root.id}',
		'parent_level': root.level,
	})

	rereply1 = comments.comment_for_client(alice_client, post.id, {
		'body': 'no u',
		'parent_fullname': f't3_{reply1.id}',
		'parent_level': reply1.level,
	})

	reply2 = comments.comment_for_client(alice_client, post.id, {
		'body': 'Good poast',
		'parent_fullname': f't3_{root.id}',
		'parent_level': root.level,
	})

	assert 3 == db.query(Comment).filter_by(id=root.id).first().descendant_count
	assert 1 == db.query(Comment).filter_by(id=reply1.id).first().descendant_count
	assert 0 == db.query(Comment).filter_by(id=reply2.id).first().descendant_count
	assert 0 == db.query(Comment).filter_by(id=rereply1.id).first().descendant_count

@util.no_rate_limit
def test_more_button_label_in_deep_threads(accounts, submissions, comments):
	db = db_session()
	alice_client, alice = accounts.client_and_user_for_account('Alice')

	post = submissions.submission_for_client(alice_client, {
		'title': 'Counting thread',
		'body': 'Count to 25',
	})
	post_id = post.id

	c = comments.comment_for_client(alice_client, post.id, {
		'body': '1',
	})
	for i in range(1, 25 + 1):
		c = comments.comment_for_client(alice_client, post.id, {
			'body': str(i),
			'parent_fullname': f't3_{c.id}',
			'parent_level': c.level,
		})
		if i % 5 == 0:
			# only look every 5 posts to make this test not _too_ unbearably slow
			view_post_response = alice_client.get(f'/post/{post.id}')
			assert 200 == view_post_response.status_code
			if i <= 8:
				assert f'More comments ({i - 8})' not in view_post_response.text
			else:
				assert f'More comments ({i - 8})' in view_post_response.text

@util.no_rate_limit
def test_bulk_update_descendant_count_quick(accounts, submissions, comments):
	"""
	1. Add two thin/non-robust posts with 20 nested comments each. Do not properly set descendant_count
	2. Do the descendant_count bulk update thing
	3. Ensure that the descendant_counts are correct
	4. Delete the comments/posts
	"""
	with app.app_context():
		db = db_session()

		lastname = ''.join(random.choice('aio') + random.choice('bfkmprst') for i in range(3))
		alice = User(**{
			"username": f"alice_{lastname}",
			"original_username": f"alice_{lastname}",
			"admin_level": 0,
			"password":"themotteuser",
			"email":None,
			"ban_evade":0,
			"profileurl":"/e/feather.webp"
		})
		db.add(alice)
		db.commit()
		posts = []
		for i in range(2):
			post = Submission(**{
				'private': False,
				'club': None,
				'author_id': alice.id,
				'over_18': False,
				'app_id': None,
				'is_bot': False,
				'url': None,
				'body': f'This is a post by {alice.username}',
				'body_html': f'This is a post by {alice.username}',
				'embed_url': None,
				'title': f'Clever unique post title number {i}',
				'title_html': f'Clever unique post title number {i}',
				'ghost': False,
				'filter_state': 'normal'
			})
			db.add(post)
			db.commit()
			posts.append(post)
			parent_comment = None
			top_comment = None
			for j in range(20):
				comment = Comment(**{
					'author_id': alice.id,
					'parent_submission': str(post.id),
					'parent_comment_id': parent_comment.id if parent_comment else None,
					'top_comment_id': top_comment.id if top_comment else None,
					'level': parent_comment.level + 1 if parent_comment else 1,
					'over_18': False,
					'is_bot': False,
					'app_id': None,
					'body_html': f'reply {i} {j}',
					'body': f'reply {i} {j}',
					'ghost': False
				})
				if parent_comment is None:
					top_comment = comment
				parent_comment = comment
				db.add(comment)
				db.commit()
		sorted_comments_0 = sorted(posts[0].comments, key=lambda c: c.id)
		sorted_comments_1 = sorted(posts[1].comments, key=lambda c: c.id)
		assert [i+1 for i in range(20)] == [c.level for c in sorted_comments_0]
		assert [i+1 for i in range(20)] == [c.level for c in sorted_comments_1]
		assert [0 for i in range(20)] == [c.descendant_count for c in sorted_comments_0]
		assert [0 for i in range(20)] == [c.descendant_count for c in sorted_comments_1]
		bulk_recompute_descendant_counts(
			lambda q: q.where(Comment.parent_submission == posts[0].id),
			db
		)
		sorted_comments_0 = sorted(posts[0].comments, key=lambda c: c.id)
		sorted_comments_1 = sorted(posts[1].comments, key=lambda c: c.id)
		assert [i+1 for i in range(20)] == [c.level for c in sorted_comments_0]
		assert [i+1 for i in range(20)] == [c.level for c in sorted_comments_1]
		assert [20-i-1 for i in range(20)] == [c.descendant_count for c in sorted_comments_0]
		assert [0 for i in range(20)] == [c.descendant_count for c in sorted_comments_1]
		for post in posts:
			for comment in post.comments:
				db.delete(comment)
			db.delete(post)
		db.commit()
