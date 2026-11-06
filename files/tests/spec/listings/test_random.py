'''
Random picks, open to anyone.

- GET /random_post redirects to the page of a post picked at random among those anyone may read: not removed or filtered, not deleted by its author, and not a draft. With no such post it is a 404.
- GET /random_user redirects to the profile of a user picked at random among all accounts.
'''
import pytest

from files.tests.spec.harness import *


def test_random_post_redirects_to_a_readable_post():
	readable = factories.post(factories.user())
	for state in [{"state_mod": "REMOVED", "state_mod_set_by": "somemod"}, {"state_mod": "FILTERED"}, {"state_user_deleted_utc": "2020-01-01T00:00:00Z"}, {"private": True}]:
		factories.post(factories.user(), **state)

	for _ in range(8):
		assert_redirect(anon().get("/random_post"), f"/post/{readable['id']}")


def test_random_post_picks_among_all_readable_posts():
	posts = [factories.post(factories.user()) for _ in range(2)]

	picked = {anon().get("/random_post").location for _ in range(40)}

	assert picked == {f"/post/{p['id']}" for p in posts}


def test_random_post_without_readable_posts_is_404():
	factories.post(factories.user(), state_mod="REMOVED", state_mod_set_by="somemod")

	assert_status(anon().get("/random_post"), 404)


@pytest.mark.parametrize("client", [anon, lambda: as_user(factories.user())])
def test_random_user_redirects_to_a_profile(client):
	r = client().get("/random_user")

	assert_status(r, 302)
	username = r.location.removeprefix("/@")
	assert r.location.startswith("/@") and db.rows("users", username=username)
