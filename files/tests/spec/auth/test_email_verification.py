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
