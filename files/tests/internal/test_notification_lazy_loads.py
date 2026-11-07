'''
Rendering the notification pages must not lazy-load relationships one row at a time: each lazy load in a loop is an N+1 query in production. The suite's lazy-load detector reports them as LazyLoadWarning.
'''
import warnings

from files.tests.conftest import LazyLoadWarning
from files.tests.spec.harness import as_user, factories


def _lazy_loads_rendering(client, path):
	with warnings.catch_warnings(record=True) as caught:
		warnings.simplefilter("always")
		r = client.get(path)
	assert r.status == 200
	return [str(w.message) for w in caught if issubclass(w.category, LazyLoadWarning)]


def test_notifications_render_without_lazy_loads():
	'''The notified reply has replies of its own, which the page doesn't render.'''
	user = factories.user()
	post = factories.post(user)
	comment = factories.comment(user, post)
	reply = factories.comment(factories.user(), post, parent=comment)
	factories.comment(factories.user(), post, parent=reply)
	factories.notification(user, reply)

	assert _lazy_loads_rendering(as_user(user), "/notifications") == []
	assert reply["body"] in as_user(user).get("/notifications").text, "the notification wasn't rendered, so this test proves nothing"


def test_a_message_page_renders_without_lazy_loads():
	sender, recipient = factories.user(), factories.user()
	message = factories.message(sender, recipient)
	answer = factories.message(recipient, sender, message)
	factories.message(sender, recipient, answer)

	assert _lazy_loads_rendering(as_user(sender), f"/comment/{answer['id']}?context=1") == []
