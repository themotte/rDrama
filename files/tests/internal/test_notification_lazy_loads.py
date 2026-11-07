'''
Rendering the notification pages must not lazy-load relationships one row at a time: each lazy load in a loop is an N+1 query in production. The suite's lazy-load detector reports them as LazyLoadWarning.
'''
import warnings

from files.tests.conftest import LazyLoadWarning
from files.tests.spec.harness import as_user, factories, seed


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


def test_the_message_tabs_render_without_lazy_loads():
	user, other, admin = factories.user(), factories.user(), factories.admin(2)
	for answerer, recipient in ((other, other), (admin, seed.MODMAIL_ID)):
		message = factories.message(user, recipient)
		answer = factories.message(answerer, user if answerer is other else recipient, message)
		factories.message(user, recipient, answer)

	assert _lazy_loads_rendering(as_user(user), "/notifications/messages") == []
	assert _lazy_loads_rendering(as_user(admin), "/notifications/modmail") == []


def _statements_rendering(client, path):
	from sqlalchemy import event
	from files.__main__ import db_session
	engine = db_session.get_bind()
	statements = []
	def count(*args): statements.append(args[2])
	event.listen(engine, "before_cursor_execute", count)
	try:
		assert client.get(path).status == 200
	finally:
		event.remove(engine, "before_cursor_execute", count)
	return len(statements)


def _replies_notified(user, n):
	'''`n` conversations, each with a notified answer two messages below its first.'''
	for _ in range(n):
		other = factories.user()
		message = factories.message(other, user)
		answer = factories.message(user, other, message)
		factories.notification(user, factories.message(other, user, answer))


def test_message_notifications_render_in_a_fixed_number_of_queries():
	'''Each notified message's conversation and recipient are loaded together, not per message.'''
	few, many = factories.user(), factories.user()
	_replies_notified(few, 1)
	_replies_notified(many, 5)

	assert _statements_rendering(as_user(many), "/notifications") == _statements_rendering(as_user(few), "/notifications")
