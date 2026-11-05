'''
Small lookups around user accounts:
- GET /id/<user id> redirects to the user's profile, /@<username>.
- GET /u/<name> redirects to /@<name>, whether or not such a user exists (links in Reddit's style).
- GET /@<username> (without the trailing slash) serves the profile like /@<username>/.
- GET /is_available/<name> tells signup whether a username is free, as {"<name>": true|false} (the name with surrounding whitespace removed). A name signup would refuse isn't available: one shorter than 3 or longer than 25 characters, or with characters other than ASCII letters, digits, "_" and "-". Nor is one that is any user's current or original username, compared case-insensitively.
- GET /@<username>/profilecss serves the custom CSS the user set for their profile page (empty if none).
- GET /2faqr/<secret> draws the QR code an authenticator app scans to set up two-factor login with that secret for the logged-in user, as a PNG.
'''
from urllib.parse import quote

import pytest

from files.tests.spec.harness import *

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


# /id/<user id>

def test_user_id_redirects_to_the_profile():
	u = factories.user()

	r = anon().get(f"/id/{u['id']}")

	assert_redirect(r, f"/@{u['username']}")


def test_unknown_user_id_is_not_found():
	u = factories.user()
	db.delete("users", id=u["id"])

	r = anon().get(f"/id/{u['id']}")

	assert_status(r, 404)


def test_non_numeric_user_id_is_not_found():
	r = anon().get("/id/abc")

	assert_status(r, 404)


# /u/<name>

def test_reddit_style_link_redirects_to_the_profile():
	u = factories.user()

	r = anon().get(f"/u/{u['username']}")

	assert_redirect(r, f"/@{u['username']}")


def test_reddit_style_link_redirects_for_unknown_names_too():
	name = factories.unique()

	r = anon().get(f"/u/{name}")

	assert_redirect(r, f"/@{name}")


# /@<username>

def test_profile_without_trailing_slash_is_the_profile():
	u = factories.user(bio_html=f"<p>{factories.unique()}</p>")

	r = anon().get(f"/@{u['username']}")

	assert_html(r, 200)
	assert_in_payload(r, u["bio_html"])


# /is_available/<name>

def test_free_name_is_available():
	name = factories.unique("free")

	r = anon().get(f"/is_available/{name}")

	assert_status(r, 200)
	assert r.json == {name: True}


def test_current_username_is_not_available_in_any_letter_case():
	u = factories.user()
	name = u["username"].upper()

	r = anon().get(f"/is_available/{name}")

	assert_status(r, 200)
	assert r.json == {name: False}


def test_original_username_is_not_available():
	u = factories.user(original_username=factories.unique("orig"))

	r = anon().get(f"/is_available/{u['original_username']}")

	assert_status(r, 200)
	assert r.json == {u["original_username"]: False}


@pytest.mark.parametrize("length, available", [(2, False), (3, True), (25, True), (26, False)])
def test_name_length_bounds_availability(length, available):
	name = "q" * length

	r = anon().get(f"/is_available/{name}")

	assert_status(r, 200)
	assert r.json == {name: available}


@pytest.mark.parametrize("name", ["has space", "dot.ted", "per%cent", "été"])
def test_names_signup_would_refuse_are_not_available(name):
	r = anon().get(f"/is_available/{quote(name)}")

	assert_status(r, 200)
	assert r.json == {name: False}


@pytest.mark.parametrize("name", ["under_score", "da-sh", "MiXed123"])
def test_names_of_letters_digits_underscores_and_dashes_are_available(name):
	r = anon().get(f"/is_available/{name}")

	assert_status(r, 200)
	assert r.json == {name: True}


def test_surrounding_whitespace_is_ignored():
	name = factories.unique("pad")

	r = anon().get(f"/is_available/%20{name}%20")

	assert_status(r, 200)
	assert r.json == {name: True}


# /@<username>/profilecss

def test_profile_css_is_served():
	css = f"body {{ color: red }} /* {factories.unique()} */"
	u = factories.user(profilecss=css)

	r = anon().get(f"/@{u['username']}/profilecss")

	assert_status(r, 200)
	assert r.text == css


def test_profile_css_is_empty_when_unset():
	u = factories.user()

	r = anon().get(f"/@{u['username']}/profilecss")

	assert_status(r, 200)
	assert r.text == ""


def test_profile_css_of_an_unknown_user_is_not_found():
	r = anon().get(f"/@{factories.unique()}/profilecss")

	assert_status(r, 404)


# /2faqr/<secret>

def test_two_factor_qr_code_is_a_png():
	r = as_user(factories.user()).get("/2faqr/JBSWY3DPEHPK3PXP")

	assert_status(r, 200)
	assert r.header("Content-Type") == "image/png"
	assert r.body.startswith(PNG_SIGNATURE)


def test_two_factor_qr_code_sends_anonymous_browsers_to_log_in():
	r = anon().get("/2faqr/JBSWY3DPEHPK3PXP")

	assert_login_redirect(r, "/2faqr/JBSWY3DPEHPK3PXP")
