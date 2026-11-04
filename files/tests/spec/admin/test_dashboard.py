'''
The admin dashboard and the site-wide switches on it:
- GET /admin is the dashboard, for admins of level 2 and up.
- POST /admin/site_settings/<setting> changes one runtime site setting (the settings file, see config.site_settings_path), for level-3 admins. Without "new_value" it flips a boolean setting; with "new_value" it stores that integer in an integer setting. It answers JSON, logs a mod action whose kind names the change ("enabled_<setting>", "disabled_<setting>" or "set_<value>_for_<setting>", spaces as underscores, cut to 32 characters), and tells every other level-3 admin through a modmail notification.
- POST /admin/dump_cache, for level-2 admins, makes the site rebuild every listing it has cached.
'''
import json
from urllib.parse import quote

import pytest

from files.tests.spec.harness import *

BOOLEAN_SETTINGS = ["Bots", "Read-only mode", "Signups", "FilterNewPosts"]
INTEGER_SETTINGS = ["FilterCommentsMinComments", "FilterCommentsMinKarma", "FilterCommentsMinAgeDays", "min_comments_private_profile", "min_truescore_private_profile", "min_age_days_private_profile"]


def _settings():
	with open(config.site_settings_path()) as f:
		return json.load(f)


def test_the_dashboard_renders_for_level_2_admins():
	assert_html(as_user(factories.admin(2)).get("/admin"), 200)


@pytest.mark.parametrize("setting", BOOLEAN_SETTINGS)
@pytest.mark.parametrize("before", [False, True], ids=["enabling", "disabling"])
def test_admin_flips_a_boolean_setting(setting, before):
	site_settings_set(setting, before)
	expected = {**_settings(), setting: not before}
	admin = factories.admin(3)
	client = as_user(admin)

	with db_diff() as d:
		r = client.post(f"/admin/site_settings/{quote(setting)}")

	assert_json_message(r)
	assert _settings() == expected
	kind = f"{'disabled' if before else 'enabled'}_{setting}".replace(" ", "_")
	d.assert_exactly(inserted={
		"modactions": [{"kind": kind, "user_id": admin["id"], "target_user_id": None, "target_submission_id": None, "target_comment_id": None}],
		"comments": [{"author_id": seed.SYSTEM_ID, "sentto": seed.AUTOJANNY_ID, "parent_submission": None}],
	})


@pytest.mark.parametrize("setting", INTEGER_SETTINGS)
def test_admin_sets_an_integer_setting(setting):
	expected = {**_settings(), setting: 7}
	admin = factories.admin(3)
	client = as_user(admin)

	with db_diff() as d:
		r = client.post(f"/admin/site_settings/{setting}", {"new_value": "7"})

	assert_json_message(r)
	assert _settings() == expected
	d.assert_exactly(inserted={
		"modactions": [{"kind": f"set_7_for_{setting}"[:32], "user_id": admin["id"], "target_user_id": None, "target_submission_id": None, "target_comment_id": None}],
		"comments": [{"author_id": seed.SYSTEM_ID, "sentto": seed.AUTOJANNY_ID, "parent_submission": None}],
	})


def test_a_setting_change_notifies_the_other_level_3_admins():
	admin = factories.admin(3)
	others = [factories.admin(3), factories.admin(3)]
	factories.admin(2)
	client = as_user(admin)

	with db_diff() as d:
		r = client.post("/admin/site_settings/FilterNewPosts")

	assert_json_message(r)
	message = d.inserted["comments"][0]["id"] if d.inserted.get("comments") else None
	d.assert_exactly(inserted={
		"modactions": [{"kind": "enabled_FilterNewPosts"}],
		"comments": [{"id": message, "author_id": seed.SYSTEM_ID, "sentto": seed.AUTOJANNY_ID, "parent_submission": None, "top_comment_id": message, "level": 1, "state_mod": "VISIBLE"}],
		"notifications": [{"comment_id": message, "user_id": other["id"]} for other in others],
	})


def test_dumping_the_cache_rebuilds_cached_listings():
	anon().get("/")
	title = factories.unique("title")
	factories.post(factories.user(), title=title)

	assert_json_message(as_user(factories.admin(2)).post("/admin/dump_cache"))

	assert_in_payload(anon().get("/"), title)
