'''
Small lookups around user accounts:
- GET /id/<user id> redirects to the user's profile, /@<username>.
- GET /u/<name> redirects to /@<name>, whether or not such a user exists (links in Reddit's style).
- GET /@<username> (without the trailing slash) serves the profile like /@<username>/.
- GET /is_available/<name> tells signup whether a username is free, as {"<name>": true|false} (the name with surrounding whitespace removed). A name signup would refuse isn't available: one shorter than 3 or longer than 25 characters, or with characters other than ASCII letters, digits, "_" and "-". Nor is one that is any user's current or original username, compared case-insensitively.
- GET /@<username>/profilecss serves the custom CSS the user set for their profile page (empty if none), as text/css.
- GET /pp/<user id> (the address mentions embed), /uid/<user id>/pic, /uid/<user id>/pic/profile and /@<username>/pic redirect (302) to the user's profile picture, wherever it's hosted: the "profile_url" of their /info. Browsers may keep the redirect for five minutes.
- GET /2faqr/<secret> draws the QR code an authenticator app scans to set up two-factor login with that secret for the logged-in user, as a PNG. It carries the secret, so it's sent with "Cache-Control: no-store": nothing may keep it.
'''
from urllib.parse import quote, urljoin

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


def test_profile_css_is_served_as_css():
	u = factories.user(profilecss="body {}")

	r = anon().get(f"/@{u['username']}/profilecss")

	assert_status(r, 200)
	assert [v.split(";")[0] for v in r.header_all("Content-Type")] == ["text/css"]


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


def test_two_factor_qr_code_is_never_stored():
	r = as_user(factories.user()).get("/2faqr/JBSWY3DPEHPK3PXP")

	assert r.header("Cache-Control") == "no-store"


def test_two_factor_qr_code_sends_anonymous_browsers_to_log_in():
	r = anon().get("/2faqr/JBSWY3DPEHPK3PXP")

	assert_login_redirect(r, "/2faqr/JBSWY3DPEHPK3PXP")


# Profile pictures

PICTURE_ROUTES = {
	"/pp/<id>": lambda u: f"/pp/{u['id']}",
	"/uid/<id>/pic": lambda u: f"/uid/{u['id']}/pic",
	"/uid/<id>/pic/profile": lambda u: f"/uid/{u['id']}/pic/profile",
	"/@<username>/pic": lambda u: f"/@{u['username']}/pic",
}


def _profile_url(user):
	return as_user(factories.user()).get(f"/@{user['username']}/info").json["profile_url"]


def _with_uploaded_picture():
	user = factories.user()
	assert_html(as_user(user).post("/settings/images/profile", files={"profile": uploads.png(20, 20)}), 200)
	return user


@pytest.mark.parametrize("route", PICTURE_ROUTES)
@pytest.mark.parametrize("picture", ["uploaded", "default", "off-site"])
def test_picture_routes_lead_to_the_users_picture(route, picture):
	user = {"uploaded": _with_uploaded_picture, "default": factories.user, "off-site": lambda: factories.user(profileurl="https://i.imgur.com/abc.png")}[picture]()
	expected = _profile_url(user)

	r = anon().get(PICTURE_ROUTES[route](user))

	assert_status(r, 302)
	assert urljoin(config.site_url(), r.location) == urljoin(config.site_url(), expected)
	assert "max-age=300" in r.header("Cache-Control")
	if picture != "off-site":
		assert_serves_image(expected)


@pytest.mark.parametrize("route", PICTURE_ROUTES)
def test_picture_routes_of_an_unknown_user_are_not_found(route):
	r = anon().get(PICTURE_ROUTES[route]({"id": factories.user()["id"] + 1000, "username": factories.unique()}))

	assert_status(r, 404)
