'''
Signing up: GET /signup issues a form whose "formkey" and "now" fields are signed for this browser (format in harness/session.py) and work once; POST /signup takes "usernametwo", "password", "password_confirm", "email" (may be empty) and "referred_by" (the referring account's id, from ?ref=<username> on the form), creates the account, logs it in and greets it with a notification. A refused signup goes back to the form with an "error" (and "ref") in the query.
'''
import pytest

from files.tests.spec.harness import *


def _form(client, **params):
	return client.get("/signup", params=params or None)


def _signup(client, form=None, **fields):
	form = form or _form(client)
	return client.post_raw("/signup", {"formkey": form.form_field("formkey"), "now": form.form_field("now"), "usernametwo": factories.unique("new"), "email": "", "password": factories.PASSWORD, "password_confirm": factories.PASSWORD, **fields})


def _login(client, user):
	client.post_raw("/login", {"username": user["username"], "password": factories.PASSWORD})


@pytest.fixture(autouse=True)
def an_existing_member():
	'''The first signup on a site holding only the system accounts is special (see the first-admin tests), so the others start with a member present.'''
	return factories.user()


# The form

def test_the_form():
	r = _form(anon())

	assert_html(r, 200)
	assert r.form_field("formkey") is not None


def test_a_logged_in_visitor_is_sent_home():
	assert_redirect(_form(as_user(factories.user())), "")


def test_the_form_is_closed_while_signups_are_off():
	site_settings_set("Signups", False)

	assert_status(_form(anon()), 403)


def test_a_referral_from_an_account_this_browser_used_is_refused():
	referrer = factories.user()
	client = anon()
	_login(client, referrer)
	client.get("/logout")

	r = _form(client, ref=referrer["username"])

	assert_html(r, 200)
	assert r.form_field("formkey") is None


# Signing up

def test_signing_up_creates_the_account_logs_it_in_and_greets_it():
	client = anon()
	username = factories.unique("new")

	with db_diff() as d:
		r = _signup(client, usernametwo=username)

	assert_redirect(r, "")
	new = db.row("users", username=username)
	assert client.user_id == new["id"]
	d.assert_exactly(inserted={
		"users": [{"username": username, "original_username": username, "admin_level": 0, "email": None, "is_activated": False, "referred_by": None, "ban_evade": 0}],
		"comments": [{"author_id": 1}],
		"notifications": [{"user_id": new["id"]}],
	})
	assert sent_mail() == []


def test_signing_up_with_an_email_mails_a_verification_link():
	email = f"{factories.unique()}@example.com"

	_signup(anon(), email=f" {email.upper()} ")

	[mail] = sent_mail()
	assert mail["to"] == [email]
	assert any("/activate?" in url for url in urls_in(mail["body"]))


def test_signing_up_from_a_browser_that_used_other_accounts_records_them_as_alts():
	earlier = factories.user()
	client = anon()
	_login(client, earlier)
	client.get("/logout")
	username = factories.unique("new")

	_signup(client, usernametwo=username)

	new = db.row("users", username=username)
	assert db.rows("alts", user2=new["id"]) == [{"user1": earlier["id"], "user2": new["id"], "is_manual": False}]


def _refused(client, form=None, **fields):
	with db_diff() as d:
		r = _signup(client, form, **fields)
	assert_redirect(r, "/signup", query_keys=("error",))
	d.assert_exactly()
	assert client.user_id is None


def test_a_wrong_form_key_is_refused():
	_refused(anon(), formkey="0" * 32)


def test_passwords_that_differ_are_refused():
	_refused(anon(), password_confirm="another " + factories.PASSWORD)


@pytest.mark.parametrize("username", ["a", "has space", "x" * 26, "émoji"])
def test_bad_usernames_are_refused(username):
	_refused(anon(), usernametwo=username)


@pytest.mark.parametrize("password", ["short", "x" * 101])
def test_passwords_of_the_wrong_length_are_refused(password):
	_refused(anon(), password=password, password_confirm=password)


def test_a_bad_email_is_refused():
	_refused(anon(), email="not-an-email")


@pytest.mark.parametrize("which", ["username", "original_username"])
def test_a_name_already_in_use_is_refused(which):
	taken = factories.user(original_username=factories.unique("orig"))

	_refused(anon(), usernametwo=taken[which].upper())


def test_a_refusal_keeps_the_referral():
	referrer = factories.user()

	r = _signup(anon(), password_confirm="different", referred_by=referrer["id"])

	assert_redirect(r, "/signup", query_keys=("error", "ref"))


def test_a_reserved_name_leads_to_its_page():
	reserved = factories.user(reserved="someone else")

	with db_diff() as d:
		r = _signup(anon(), usernametwo=reserved["username"])

	assert_redirect(r, f"/@{reserved['username']}")
	d.assert_exactly()


def test_a_post_without_the_form_is_refused():
	client = anon()

	with db_diff() as d:
		r = client.post_raw("/signup", {"usernametwo": factories.unique("new"), "email": "", "password": factories.PASSWORD, "password_confirm": factories.PASSWORD})

	assert_status(r, 400)
	d.assert_exactly()


def test_the_form_works_once():
	client = anon()
	form = _form(client)
	_signup(client, form)
	client.get("/logout")

	with db_diff() as d:
		r = _signup(client, form)

	assert_status(r, 400)
	d.assert_exactly()


def test_signing_up_is_refused_while_signups_are_off():
	client = anon()
	form = _form(client)
	site_settings_set("Signups", False)

	with db_diff() as d:
		r = _signup(client, form)

	assert_status(r, 403)
	d.assert_exactly()


def test_an_api_client_cannot_sign_up():
	'''Only an API client reaches this: a logged-in browser's signup post carries no form key of the account's, so it counts as anonymous.'''
	client = as_api(factories.api_token(factories.user()))

	with db_diff() as d:
		r = client.post_raw("/signup", {"usernametwo": factories.unique("new")})

	assert_status(r, 403)
	d.assert_exactly()


# Referrals

def test_a_referral_is_recorded_and_earns_the_first_recruiter_badge():
	referrer = factories.user()
	username = factories.unique("new")

	_signup(anon(), usernametwo=username, referred_by=referrer["id"])

	assert db.row("users", username=username)["referred_by"] == referrer["id"]
	assert [b["badge_id"] for b in db.rows("badges", user_id=referrer["id"])] == [10]
	assert len(db.rows("notifications", user_id=referrer["id"])) == 1


@pytest.mark.parametrize("earlier, held, earned", [(9, [], [10, 11]), (9, [10], [11]), (99, [10, 11], [12]), (99, [10, 11, 12], [])], ids=["catching up", "tenth", "hundredth", "all held"])
def test_more_referrals_earn_the_higher_recruiter_badges(earlier, held, earned):
	referrer = factories.user()
	for _ in range(earlier):
		factories.user(referred_by=referrer["id"])
	for badge in held:
		db.insert("badges", user_id=referrer["id"], badge_id=badge)

	with db_diff() as d:
		_signup(anon(), referred_by=referrer["id"])

	assert sorted(row["badge_id"] for row in d.inserted.get("badges", [])) == earned
	assert len([n for n in d.inserted["notifications"] if n["user_id"] == referrer["id"]]) == len(earned)


# Ban evasion

@pytest.mark.parametrize("ban", [{"is_banned": 1}, {"shadowbanned": "someone"}], ids=["banned", "shadowbanned"])
def test_signing_up_from_a_banned_accounts_browser_flags_ban_evasion(ban):
	banned = factories.user(**ban)
	client = anon()
	_login(client, banned)
	client.get("/logout")
	username = factories.unique("new")

	_signup(client, usernametwo=username)

	assert db.row("users", username=username)["ban_evade"] == 1


def test_a_temporary_ban_is_not_ban_evasion():
	banned = factories.user(is_banned=1, unban_utc=2_000_000_000)
	client = anon()
	_login(client, banned)
	client.get("/logout")
	username = factories.unique("new")

	_signup(client, usernametwo=username)

	assert db.row("users", username=username)["ban_evade"] == 0


# The first admin: on a fresh site, the first person to sign up runs it

@pytest.mark.parametrize("an_existing_member", [None])
def test_the_first_signup_on_a_fresh_site_becomes_a_full_admin(an_existing_member):
	username = factories.unique("first")

	_signup(anon(), usernametwo=username)

	assert db.row("users", username=username)["admin_level"] == 3


def test_later_signups_are_not_admins():
	username = factories.unique("new")

	_signup(anon(), usernametwo=username)

	assert db.row("users", username=username)["admin_level"] == 0


# Malformed posts

def test_a_signup_without_an_email_field_has_no_email():
	client = anon()
	form = _form(client)
	username = factories.unique("new")

	r = client.post_raw("/signup", {"formkey": form.form_field("formkey"), "now": form.form_field("now"), "usernametwo": username, "password": factories.PASSWORD, "password_confirm": factories.PASSWORD})

	assert_redirect(r, "")
	assert db.row("users", username=username)["email"] is None


def test_a_signup_without_passwords_is_refused():
	client = anon()
	form = _form(client)

	with db_diff() as d:
		r = client.post_raw("/signup", {"formkey": form.form_field("formkey"), "now": form.form_field("now"), "usernametwo": factories.unique("new"), "email": ""})

	assert_redirect(r, "/signup", query_keys=("error",))
	d.assert_exactly()


@pytest.mark.parametrize("referred_by", ["", "someone", "unknown"])
def test_a_referral_naming_no_account_is_refused(referred_by):
	gone = factories.user()
	db.delete("users", id=gone["id"])
	client = anon()
	form = _form(client)

	with db_diff() as d:
		r = _signup(client, form, referred_by=gone["id"] if referred_by == "unknown" else referred_by)

	assert_status(r, 400)
	d.assert_exactly()
