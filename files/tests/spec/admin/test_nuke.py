'''
POST /admin/nuke_user and POST /admin/unnuke_user act on everything the user named by "user" wrote, log it in the mod log, and send the admin to that user's profile. Nuking removes every post and comment not already removed (held ones included); unnuking restores every removed one, whoever removed it, and leaves held ones in the filter queue. Either way, items whose visibility changes have the same effects as a moderator removing or approving them one by one: counts follow, and restored items notify as approving them would. System accounts can't be nuked.
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


def test_nuking_removes_everything_the_user_wrote():
	user = factories.user()
	post, held_post = factories.post(user), factories.post(user, state_mod="FILTERED")
	other_post = factories.post(factories.user())
	parent = factories.comment(factories.user(), other_post)
	reply = factories.comment(user, other_post, parent)
	removed_comment = factories.comment(user, other_post, state_mod="REMOVED")
	admin = factories.admin(3)

	with db_diff() as d:
		r = as_user(admin).post("/admin/nuke_user", {"user": user["username"]})

	assert_redirect(r, f"/@{user['username']}")
	removed = {"state_mod": "REMOVED", "state_mod_set_by": admin["username"]}
	d.assert_exactly(
		updated={
			"submissions": {post["id"]: removed, held_post["id"]: removed, other_post["id"]: {"comment_count": 1}},
			"comments": {reply["id"]: removed, parent["id"]: {"descendant_count": 0}},
			"users": {user["id"]: {"post_count": 0, "comment_count": 0}},
		},
		inserted={"modactions": [{"kind": "nuke_user", "user_id": admin["id"], "target_user_id": user["id"]}]},
	)
	assert db.row("comments", id=removed_comment["id"])["state_mod_set_by"] is None


def test_unnuking_restores_removed_items_and_leaves_held_ones():
	user = factories.user()
	post, held_post = factories.post(user, state_mod="REMOVED"), factories.post(user, state_mod="FILTERED")
	other_post = factories.post(factories.user())
	parent = factories.comment(factories.user(), other_post)
	reply = factories.comment(user, other_post, parent, state_mod="REMOVED")
	admin = factories.admin(3)

	with db_diff() as d:
		r = as_user(admin).post("/admin/unnuke_user", {"user": user["username"]})

	assert_redirect(r, f"/@{user['username']}")
	restored = {"state_mod": "VISIBLE", "state_mod_set_by": admin["username"]}
	d.assert_exactly(
		updated={
			"submissions": {post["id"]: restored, other_post["id"]: {"comment_count": 2}},
			"comments": {reply["id"]: restored, parent["id"]: {"descendant_count": 1}},
			"users": {user["id"]: {"post_count": 1, "comment_count": 1}},
		},
		inserted={
			"modactions": [{"kind": "unnuke_user", "user_id": admin["id"], "target_user_id": user["id"]}],
			"notifications": [{"user_id": parent["author_id"], "comment_id": reply["id"]}],
		},
	)


@pytest.mark.parametrize("action", ["nuke_user", "unnuke_user"])
def test_system_accounts_cannot_be_nuked(action):
	admin = factories.admin(3)

	with db_diff() as d:
		r = as_user(admin).post(f"/admin/{action}", {"user": "AutoJanny"}, headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("action", ["nuke_user", "unnuke_user"])
def test_nuking_without_naming_a_user_is_refused(action):
	client = as_user(factories.admin(3))

	with db_diff() as d:
		r = client.post(f"/admin/{action}", headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


@pytest.mark.parametrize("action", ["nuke_user", "unnuke_user"])
def test_nuking_an_unknown_user_is_not_found(action):
	admin = factories.admin(3)

	with db_diff() as d:
		r = as_user(admin).post(f"/admin/{action}", {"user": factories.unique()}, headers=XHR)

	assert_status(r, 404)
	d.assert_exactly()
