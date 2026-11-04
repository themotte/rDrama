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


def test_asking_for_a_verification_mails_a_link_to_the_accounts_address():
	u = factories.user(email=f"{factories.unique()}@example.com")

	r = as_user(u).post("/verify_email", headers=XHR)

	assert_json_message(r)
	[mail] = sent_mail()
	assert mail["to"] == [u["email"]]
	assert any(url.startswith(f"{config.site_url()}/activate?") for url in urls_in(mail["body"]))


def test_a_link_verifies_its_address():
	u = factories.user()
	email = f"{factories.unique()}@example.com"

	with db_diff() as d:
		r = as_user(u).get("/activate", params=_link_params(u, email, int(time.time())))

	assert_html(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {"email": email, "is_activated": True}}})


def test_a_logged_out_visitor_logs_in_first():
	u = factories.user()
	params = _link_params(u, f"{factories.unique()}@example.com", int(time.time()))

	r = anon().get("/activate", params=params)

	assert r.status == 302 and r.location.startswith("/login?redirect=")


def test_a_link_with_an_invalid_address_is_refused():
	u = factories.user()

	assert_html(as_user(u).get("/activate", params=_link_params(u, "not-an-email", int(time.time()))), 400)


def test_an_expired_link_changes_nothing():
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).get("/activate", params=_link_params(u, f"{factories.unique()}@example.com", int(time.time()) - 3601))

	assert_html(r, 410)
	d.assert_exactly()


def test_a_link_with_a_bad_token_is_refused():
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).get("/activate", params={**_link_params(u, f"{factories.unique()}@example.com", int(time.time())), "token": "0" * 32})

	assert_status(r, 403)
	d.assert_exactly()


def test_a_link_for_the_address_already_verified_changes_nothing():
	email = f"{factories.unique()}@example.com"
	u = factories.user(email=email, is_activated=True)

	with db_diff() as d:
		r = as_user(u).get("/activate", params=_link_params(u, email, int(time.time())))

	assert_html(r, 200)
	d.assert_exactly()


def test_a_link_with_a_malformed_time_is_refused():
	u = factories.user()

	assert_status(as_user(u).get("/activate", params={**_link_params(u, f"{factories.unique()}@example.com", int(time.time())), "time": "soon"}), 400)


def test_asking_for_a_verification_without_an_email_is_refused():
	r = as_user(factories.user()).post("/verify_email", headers=XHR)

	assert_status(r, 400)
	assert sent_mail() == []


def test_a_link_for_the_accounts_own_unverified_address_verifies_it():
	email = f"{factories.unique()}@example.com"
	u = factories.user(email=email, is_activated=False)

	with db_diff() as d:
		r = as_user(u).get("/activate", params=_link_params(u, email, int(time.time())))

	assert_html(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {"is_activated": True}}})
