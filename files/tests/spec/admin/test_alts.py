'''
Alt accounts, as admins record and compare them:
- POST /admin/link_accounts records that the users with ids "u1" and "u2" are the same person, as a manual link, logs it in the mod log against "u1", noting `with <u2>` (an entry only admins see), and shows the two users' vote comparison. Linking an account to itself or to an account it's already linked to, or naming an account that doesn't exist, is refused with 400.
- GET /admin/alt_votes compares the voting of the users named "u1" and "u2"; without both it shows an empty comparison form.
'''
import pytest

from files.tests.spec.harness import *


def test_admin_links_two_accounts():
	u1, u2 = factories.user(), factories.user()
	admin = factories.admin(2)

	with db_diff() as d:
		r = as_user(admin).post("/admin/link_accounts", {"u1": u1["id"], "u2": u2["id"]})

	assert_redirect(r, "/admin/alt_votes", query_keys=["u1", "u2"])
	d.assert_exactly(inserted={
		"alts": [{"user1": u1["id"], "user2": u2["id"], "is_manual": True}],
		"modactions": [{"kind": "link_accounts", "user_id": admin["id"], "target_user_id": u1["id"], "target_submission_id": None, "target_comment_id": None, "_note": f"with {u2['id']}"}],
	})


def test_linking_leads_to_the_two_users_vote_comparison():
	u1, u2 = factories.user(), factories.user()
	client = as_user(factories.admin(2))
	location = client.post("/admin/link_accounts", {"u1": u1["id"], "u2": u2["id"]}).location

	r = client.get(location)

	assert_html(r, 200)
	assert_in_payload(r, u1["username"])
	assert_in_payload(r, u2["username"])


@pytest.mark.parametrize("case", ["itself", "linked", "linked the other way", "unknown", "not an id"])
def test_a_link_that_adds_nothing_is_refused(case):
	u1, u2 = factories.user(), factories.user()
	if case == "linked": db.insert("alts", user1=u1["id"], user2=u2["id"], is_manual=False)
	if case == "linked the other way": db.insert("alts", user1=u2["id"], user2=u1["id"], is_manual=False)
	other = {"itself": u1["id"], "unknown": db.execute("SELECT nextval('users_id_seq')"), "not an id": "someone"}.get(case, u2["id"])
	client = as_user(factories.admin(2))

	with db_diff() as d:
		r = client.post("/admin/link_accounts", {"u1": u1["id"], "u2": other}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


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
