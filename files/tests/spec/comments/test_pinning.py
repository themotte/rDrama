'''
Only admins pin comments to the top of their thread (POST /sticky_comment/<comment id>, see the admin area). A post's author has no way to pin comments on their post.
'''
from files.tests.spec.harness import *


def test_post_authors_cant_pin_comments_on_their_post():
	op = factories.user()
	comment = factories.comment(factories.user(), factories.post(op))
	client = as_user(op)

	with db_diff() as d:
		r = client.post(f"/pin_comment/{comment['id']}", headers=XHR)

	assert_status(r, 404)
	d.assert_exactly()
