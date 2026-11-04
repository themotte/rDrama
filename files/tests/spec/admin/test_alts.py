'''
Alt accounts, as admins record and compare them:
- POST /admin/link_accounts records that the users with ids "u1" and "u2" are the same person, as a manual link, and logs it in the mod log against "u1".
- GET /admin/alt_votes compares the voting of the users named "u1" and "u2"; without both it shows an empty comparison form.
'''
from files.tests.spec.harness import *


def test_admin_links_two_accounts():
	u1, u2 = factories.user(), factories.user()
	admin = factories.admin(2)

	with db_diff() as d:
		r = as_user(admin).post("/admin/link_accounts", {"u1": u1["id"], "u2": u2["id"]})

	assert_status(r, 302)
	d.assert_exactly(inserted={
		"alts": [{"user1": u1["id"], "user2": u2["id"], "is_manual": True}],
		"modactions": [{"kind": "link_accounts", "user_id": admin["id"], "target_user_id": u1["id"], "target_submission_id": None, "target_comment_id": None}],
	})


def test_alt_vote_comparison_form():
	r = as_user(factories.admin(2)).get("/admin/alt_votes")

	assert_html(r, 200)


def test_alt_vote_comparison_names_both_users():
	u1, u2 = factories.user(), factories.user()

	r = as_user(factories.admin(2)).get("/admin/alt_votes", params={"u1": u1["username"], "u2": u2["username"]})

	assert_html(r, 200)
	assert_in_payload(r, u1["username"])
	assert_in_payload(r, u2["username"])


def test_alt_vote_comparison_with_an_unknown_user_is_not_found():
	u1 = factories.user()

	r = as_user(factories.admin(2)).get("/admin/alt_votes", params={"u1": u1["username"], "u2": factories.unique()})

	assert_status(r, 404)
