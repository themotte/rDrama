'''
POST /admin/nuke_user and POST /admin/unnuke_user remove, or restore, everything the user named by "user" posted, log it in the mod log, and send the admin to that user's profile.
'''
import pytest

from files.tests.spec.harness import *


@pytest.mark.parametrize("action, kind", [("nuke_user", "nuke_user"), ("unnuke_user", "unnuke_user")])
def test_nuking_a_user_without_content_only_logs_it(action, kind):
	user = factories.user()
	admin = factories.admin(3)

	with db_diff() as d:
		r = as_user(admin).post(f"/admin/{action}", {"user": user["username"]})

	assert_redirect(r, f"/@{user['username']}")
	d.assert_exactly(inserted={"modactions": [{"kind": kind, "user_id": admin["id"], "target_user_id": user["id"], "target_submission_id": None, "target_comment_id": None}]})


@pytest.mark.parametrize("action", ["nuke_user", "unnuke_user"])
def test_nuking_an_unknown_user_is_not_found(action):
	admin = factories.admin(3)

	with db_diff() as d:
		r = as_user(admin).post(f"/admin/{action}", {"user": factories.unique()}, headers=XHR)

	assert_status(r, 404)
	d.assert_exactly()
