from files.helpers.config.const import RENDER_DEPTH_LIMIT
from . import util_accounts
from . import util_submissions
from . import util_comments
from . import util
from flask import g
from files.__main__ import app, db_session
from files.classes import Submission, Comment, User
from files.classes.visstate import StateMod
from files.helpers.comments import bulk_recompute_descendant_counts
import json
import time as _time


def assert_comment_visibility(post, comment_body, clients):
	for client_name, (client, should_see) in clients.items():
		response = client.get(f'/post/{post.id}')
		if should_see:
			assert comment_body in response.text, f'{client_name} should see comment'
		else:
			assert comment_body not in response.text, f'{client_name} should not see comment'

def test_submission_comment_count():
	"""
	Scenario:
		1. There is a submission
		2. Bob the badpoaster poasts a comment on the submission
		3. submission.comment_count goes up by 1. Everyone can see the comment.
		4. Alice the admin removes the comment
		5. submission.comment_count goes down by 1. Only Bob and admins can see the comment.
	"""
	alice_client, alice = util_accounts.create_test_client_and_admin(2, 'Alice')

	bob_client, bob = util_accounts.create_test_client_and_user('Bob')
	carol_client, carol = util_accounts.create_test_client_and_user('Carol')
	logged_off_client = util_accounts.create_logged_off_client()

	post = util_submissions.create_submission_for_client(alice_client, {
		'title': 'Weekly Takes',
		'body': 'Post your takes. Bad takes will be removed',
	})
	post_id = post.id

	with util.test_db_session() as db:
		post = db.query(Submission).filter_by(id=post_id).first()
		assert 0 == post.comment_count

	comment_body = 'The sun is a social construct.'
	comment = util_comments.create_comment_for_client(bob_client, post.id, {
		'body': comment_body,
	})

	with util.test_db_session() as db:
		post = db.query(Submission).filter_by(id=post_id).first()
		assert 1 == post.comment_count

	assert_comment_visibility(post, comment_body, {
		'alice': (alice_client, True),
		'bob': (bob_client, True),
		'carol': (carol_client, True),
		'guest': (logged_off_client, True),
	})

	response, _ = util.post_json_with_formkey(
		alice_client, f'/post/{post.id}', '/admin/update_filter_status',
		json_data={
			'comment_id': comment.id,
			'new_status': 'removed',
		}
	)
	assert 200 == response.status_code

	with util.test_db_session() as db:
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

def test_comment_descendant_count():
	"""
		Here is a contentious top-level comment
			You're wrong, this isn't contentious
				no u
			Good poast
	"""
	alice_client, alice = util_accounts.create_test_client_and_user('Alice')

	post = util_submissions.create_submission_for_client(alice_client, {
		'title': 'Discussion',
		'body': 'Discuss stuff',
	})
	post_id = post.id

	root = util_comments.create_comment_for_client(alice_client, post.id, {
		'body': 'Here is a contentious top-level comment',
	})

	with util.test_db_session() as db:
		assert 0 == db.query(Comment).filter_by(id=root.id).first().descendant_count

	reply1 = util_comments.create_comment_for_client(alice_client, post.id, {
		'body': 'You\'re wrong, this isn\'t contentious',
		'parent_fullname': f'comment_{root.id}',
		'parent_level': root.level,
	})

	rereply1 = util_comments.create_comment_for_client(alice_client, post.id, {
		'body': 'no u',
		'parent_fullname': f'comment_{reply1.id}',
		'parent_level': reply1.level,
	})

	reply2 = util_comments.create_comment_for_client(alice_client, post.id, {
		'body': 'Good poast',
		'parent_fullname': f'comment_{root.id}',
		'parent_level': root.level,
	})

	with util.test_db_session() as db:
		assert 3 == db.query(Comment).filter_by(id=root.id).first().descendant_count
		assert 1 == db.query(Comment).filter_by(id=reply1.id).first().descendant_count
		assert 0 == db.query(Comment).filter_by(id=reply2.id).first().descendant_count
		assert 0 == db.query(Comment).filter_by(id=rereply1.id).first().descendant_count

def test_more_button_label_in_deep_threads():
	alice_client, alice = util_accounts.create_test_client_and_user('Alice')

	post = util_submissions.create_submission_for_client(alice_client, {
		'title': 'Counting thread',
		'body': 'Count to 25',
	})
	post_id = post.id

	c = util_comments.create_comment_for_client(alice_client, post.id, {
		'body': '1',
	})
	for i in range(1, 25 + 1):
		c = util_comments.create_comment_for_client(alice_client, post.id, {
			'body': str(i),
			'parent_fullname': f'comment_{c.id}',
			'parent_level': c.level,
		})
		if i % 5 == 0:
			# only look every 5 posts to make this test not _too_ unbearably slow
			view_post_response = alice_client.get(f'/post/{post.id}')
			assert 200 == view_post_response.status_code
			if i <= RENDER_DEPTH_LIMIT - 1:
				assert f'More comments ({i - RENDER_DEPTH_LIMIT + 1})' not in view_post_response.text
			else:
				assert f'More comments ({i - RENDER_DEPTH_LIMIT + 1})' in view_post_response.text

def test_bulk_update_descendant_count_quick():
	"""
	1. Add two thin/non-robust posts with 20 nested comments each. Do not properly set descendant_count
	2. Do the descendant_count bulk update thing
	3. Ensure that the descendant_counts are correct
	4. Delete the comments/posts
	"""
	with app.app_context():
		db = db_session()

		suffix = str(int(_time.time() * 1000))[-10:]
		alice = User(**{
			"username": f"a_{suffix}",
			"original_username": f"a_{suffix}",
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
				'state_mod': StateMod.VISIBLE,
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
					'ghost': False,
					'state_mod': StateMod.VISIBLE,
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
