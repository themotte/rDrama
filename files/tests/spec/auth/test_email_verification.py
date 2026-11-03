'''
Email verification links (GET /activate?email=&id=&time=&token=; the token format is in harness/session.py): following one while logged in sets and verifies that email on the account.
'''
import time

from files.tests.spec.harness import *


def test_a_signup_form_key_never_passes_as_a_verification_token():
	attacker = factories.user()
	client = as_user(attacker)
	visitor = anon()
	issued = int(time.time())
	form = visitor.get("/signup", headers={"User-Agent": f"@x.example+{attacker['id']}+{issued}"})
	forged_email = f"{form.form_field('now')}{visitor.session()['signup_token']}@x.example"

	with db_diff() as d:
		r = client.get("/activate", params={"email": forged_email, "id": attacker["id"], "time": issued, "token": form.form_field("formkey")})

	assert_status(r, 403)
	d.assert_exactly()


def _link_params(user, email, issued):
	return {"email": email, "id": user["id"], "time": issued, "token": session.sign(f"activate+{email}+{user['id']}+{issued}")}


def test_a_link_only_verifies_while_logged_in_as_its_account():
	owner = factories.user()
	other = as_user(factories.user())

	with db_diff() as d:
		r = other.get("/activate", params=_link_params(owner, f"{factories.unique()}@example.com", int(time.time())))

	assert_status(r, 403)
	d.assert_exactly()


def test_a_link_dated_in_the_future_has_expired():
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).get("/activate", params=_link_params(u, f"{factories.unique()}@example.com", int(time.time()) + 7200))

	assert_status(r, 410)
	d.assert_exactly()
