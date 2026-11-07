'''
Messages that older versions of the site let users write where no conversation is: private replies to comments on posts, and replies to the site's notices. They stay in the database.

A private reply to a comment on a post is never shown with that post's comments: not on the post page or more of its comments, nor on the comment's permalink or more of its thread.
'''
import pytest

from files.tests.spec.harness import *


def _private_reply_to(comment):
	'''A private reply to a comment on a post, as older versions wrote one: no post, the comment as its parent, in its thread, sent to its author.'''
	return factories.message(factories.user(), db.row("users", id=comment["author_id"]), parent=comment)


@pytest.mark.parametrize("viewer", ["visitor", "user"])
@pytest.mark.parametrize("path", ["/post/{post}", "/viewmore/{post}/old/{none}?ids={none}", "/post/{post}/x/{comment}", "/morecomments/{comment}"], ids=["post page", "view more", "permalink", "more comments"])
def test_private_replies_to_comments_are_not_shown_with_the_post(viewer, path):
	post = factories.post(factories.user())
	comment = factories.comment(factories.user(), post)
	reply = _private_reply_to(comment)
	client = anon() if viewer == "visitor" else as_user(factories.user())

	r = client.get(path.format(post=post["id"], comment=comment["id"], none=0))

	assert_status(r, 200)
	if not path.startswith("/morecomments"): assert_in_payload(r, comment["body"])
	assert_not_in_payload(r, reply["text"])
