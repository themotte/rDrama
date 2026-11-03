'''
Rendering the post page must not lazy-load relationships one row at a time: each lazy load in a loop is an N+1 query in production. The suite's lazy-load detector reports them as LazyLoadWarning.
'''
import warnings

import pytest

from files.tests.conftest import LazyLoadWarning
from files.tests.spec.harness import anon, as_user, db, factories


def _lazy_loads_rendering(client, post, about=""):
	with warnings.catch_warnings(record=True) as caught:
		warnings.simplefilter("always")
		r = client.get(f"/post/{post['id']}")
	assert r.status == 200
	return [str(w.message) for w in caught if issubclass(w.category, LazyLoadWarning) and about in str(w.message)]


def _post_with_a_reply_chain():
	post = factories.post(factories.user())
	top = factories.comment(factories.user(), post)
	factories.comment(factories.user(), post, parent=top)
	return post


@pytest.mark.parametrize("viewer", ["visitor", "user"])
def test_post_page_renders_without_lazy_loads(viewer):
	post = _post_with_a_reply_chain()
	client = anon() if viewer == "visitor" else as_user(factories.user())

	assert _lazy_loads_rendering(client, post) == []


def test_admin_post_page_renders_user_notes_without_lazy_loads():
	'''Admins see each author's notes, which refer to other posts and comments; those must be loaded together, not per note.'''
	author = factories.user()
	post = factories.post(author)
	factories.comment(author, post)
	other_post = factories.post(author)
	other_comment = factories.comment(author, other_post)
	admin = factories.admin(2)
	db.insert("usernotes", author_id=admin["id"], reference_user=author["id"], reference_comment=other_comment["id"], note="comment-ref note", tag="Comment")
	db.insert("usernotes", author_id=admin["id"], reference_user=author["id"], reference_post=other_post["id"], note="post-ref note", tag="Warning")

	assert _lazy_loads_rendering(as_user(admin), post, about="UserNote") == []
	assert "comment-ref note" in as_user(admin).get(f"/post/{post['id']}").text, "the notes weren't rendered, so this test proves nothing"
