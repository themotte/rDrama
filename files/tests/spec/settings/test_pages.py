'''
The settings pages, and who may use the settings endpoints at all.

Every settings endpoint requires login; anonymous browsers are sent to log in. Bans don't restrict preferences, but suspended users can't change their public profile, username included (see spec/users/test_suspended and test_account).
'''
import pytest

from files.tests.spec.harness import *

PAGES = ["/settings/profile", "/settings/blocks", "/settings/css", "/settings/profilecss", "/settings/apps", "/settings/content"]

POST_ENDPOINTS = [
	"/settings/profile", "/settings/filters", "/changelogsub", "/settings/namecolor", "/settings/themecolor", "/settings/titlecolor", "/settings/verifiedcolor",
	"/settings/security", "/settings/log_out_all_others", "/settings/images/profile", "/settings/images/banner", "/settings/css", "/settings/profilecss",
	"/settings/block", "/settings/unblock", "/settings/name_change", "/settings/title_change",
]


@pytest.mark.parametrize("path", PAGES)
def test_settings_page_renders_for_members(path):
	assert_html(as_user(factories.user()).get(path), 200)


@pytest.mark.parametrize("path", PAGES + ["/settings"])
def test_settings_page_requires_login(path):
	assert_login_redirect(anon().get(path), returning_to=path)


def test_settings_root_redirects_to_profile_settings():
	assert_redirect(as_user(factories.user()).get("/settings"), "/settings/profile")


@pytest.mark.parametrize("path", POST_ENDPOINTS)
def test_settings_endpoint_requires_login(path):
	with db_diff() as d:
		r = anon().post_raw(path, {"username": "x"})

	assert_login_redirect(r, returning_to=path)
	d.assert_exactly()


@pytest.mark.parametrize("ban", [{"is_banned": 1, "unban_utc": 0}, {"shadowbanned": "AutoJanny"}], ids=["permabanned", "shadowbanned"])
def test_bans_do_not_restrict_preferences(ban):
	u = factories.user(cardview=False, **ban)

	assert_json_message(as_user(u).post("/settings/profile", {"cardview": "true"}))


def test_profile_settings_page_shows_the_bio():
	token = factories.unique()

	assert_in_payload(as_user(factories.user(bio=token)).get("/settings/profile"), token)


def test_profile_settings_page_shows_when_a_locked_flair_unlocks():
	u = factories.user(flairchanged=2_000_000_000)

	assert_in_payload(as_user(u).get("/settings/profile"), "2033")


def test_content_settings_page_shows_the_filter_words():
	token = factories.unique()

	assert_in_payload(as_user(factories.user(custom_filter_list=token)).get("/settings/content"), token)


def test_apps_settings_page_lists_the_users_apps():
	u = factories.user()
	application = factories.oauth_app(u, state="pending")

	assert_in_payload(as_user(u).get("/settings/apps"), application["app_name"])
