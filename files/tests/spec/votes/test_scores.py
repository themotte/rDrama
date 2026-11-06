'''
How scores show.

Viewing a page never changes a score: a shadowbanned author viewing their own new comments, however often, leaves its votes as they are.
'''
import time

from files.tests.spec.harness import *


def test_a_shadowbanned_author_viewing_their_new_comment_changes_no_score():
	author = factories.user(shadowbanned="somemod")
	post = factories.post(factories.user())
	factories.comment(author, post, created_utc=int(time.time()) - 15 * 60)
	client = as_user(author)

	with db_diff() as d:
		for _ in range(20):
			assert_status(client.get(f"/post/{post['id']}"), 200)

	d.assert_exactly(updated={"submissions": {post["id"]: {"views": ANY}}})
