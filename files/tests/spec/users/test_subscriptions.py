'''
Subscribing to a post's comments (the subscriber is notified of new comments on it; see the comments area): POST /subscribe/<post id> and POST /unsubscribe/<post id>, for logged-in users, answer JSON with a "message". Subscribing again, or unsubscribing from a post one isn't subscribed to, changes nothing. A post that doesn't exist is 404. Anonymous browsers are sent to log in, and nothing changes.
'''
import pytest

from files.tests.spec.harness import *


def test_subscribing_to_a_post():
	user, post = factories.user(), factories.post(factories.user())

	with db_diff() as d:
		r = as_user(user).post(f"/subscribe/{post['id']}")

	assert_json_message(r)
	d.assert_exactly(inserted={"subscriptions": [{"user_id": user["id"], "submission_id": post["id"]}]})


def test_unsubscribing_from_a_post():
	user, post = factories.user(), factories.post(factories.user())
	db.insert("subscriptions", user_id=user["id"], submission_id=post["id"])

	with db_diff() as d:
		r = as_user(user).post(f"/unsubscribe/{post['id']}")

	assert_json_message(r)
	d.assert_exactly(deleted={"subscriptions": [(post["id"], user["id"])]})


def test_unsubscribing_when_not_subscribed_changes_nothing():
	user, post = factories.user(), factories.post(factories.user())
	db.insert("subscriptions", user_id=factories.user()["id"], submission_id=post["id"])

	with db_diff() as d:
		r = as_user(user).post(f"/unsubscribe/{post['id']}")

	assert_json_message(r)
	d.assert_exactly()


@pytest.mark.parametrize("action", ["/subscribe", "/unsubscribe"])
def test_subscriptions_send_anonymous_browsers_to_log_in(action):
	path = f"{action}/{factories.post(factories.user())['id']}"

	with db_diff() as d:
		r = anon().post(path)

	assert_login_redirect(r, path)
	d.assert_exactly()


def test_subscribing_again_changes_nothing():
	user, post = factories.user(), factories.post(factories.user())
	db.insert("subscriptions", user_id=user["id"], submission_id=post["id"])

	with db_diff() as d:
		r = as_user(user).post(f"/subscribe/{post['id']}")

	assert_json_message(r)
	d.assert_exactly()


def _unknown_post_id():
	return db.execute("SELECT nextval('submissions_id_seq')")


@pytest.mark.parametrize("action", ["/subscribe", "/unsubscribe"])
@pytest.mark.parametrize("post", ["unknown", "not a number"])
def test_subscriptions_to_posts_that_dont_exist_are_not_found(action, post):
	post_id = {"unknown": _unknown_post_id, "not a number": lambda: "x"}[post]()
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.post(f"{action}/{post_id}", headers=XHR)

	assert_status(r, 404)
	d.assert_exactly()
