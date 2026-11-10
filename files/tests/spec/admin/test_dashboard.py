'''
The admin dashboard and the site-wide switches on it:
- GET /admin is the dashboard, for admins of level 2 and up.
- POST /admin/site_settings/<setting> changes one runtime site setting (the settings file, see config.site_settings_path), for level-3 admins. A boolean setting takes no "new_value" and is flipped; an integer setting takes the integer to store as "new_value". Anything else is refused with 400, and an unknown setting is 404. It answers JSON, logs a mod action whose kind names the change ("enabled_<setting>", "disabled_<setting>" or "set_<value>_for_<setting>", spaces as underscores, cut to 32 characters), and tells every other level-3 admin through a modmail notification.
- POST /admin/dump_cache, for level-2 admins, makes the site recompute what it caches (the statistics pages), and logs it.
'''
import json
from urllib.parse import quote

import pytest

from files.tests.spec.harness import *

BOOLEAN_SETTINGS = [name for name, setting in config.SITE_SETTINGS.items() if setting.kind is bool]
INTEGER_SETTINGS = [name for name, setting in config.SITE_SETTINGS.items() if setting.kind is int]


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


def test_a_setting_change_notifies_the_other_admins_from_level_2():
	admin = factories.admin(3)
	others = [factories.admin(2), factories.admin(3)]
	factories.admin(1)
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


def test_the_dashboard_renders_for_level_3_admins():
	assert_html(as_user(factories.admin(3)).get("/admin"), 200)


def test_dumping_the_cache_is_logged():
	admin = factories.admin(2)

	with db_diff() as d:
		r = as_user(admin).post("/admin/dump_cache")

	assert_json_message(r)
	d.assert_exactly(inserted={"modactions": [{"kind": "dump_cache", "user_id": admin["id"]}]})


@pytest.mark.parametrize("setting, data", [
	*[pytest.param(s, {"new_value": "7"}, id=f"{s} given a value") for s in BOOLEAN_SETTINGS],
	*[pytest.param(s, {}, id=f"{s} without a value") for s in INTEGER_SETTINGS],
	*[pytest.param(s, {"new_value": v}, id=f"{s} given {v!r}") for s in INTEGER_SETTINGS[:1] for v in ("", "seven", "7.5")],
])
def test_a_setting_only_takes_a_value_of_its_kind(setting, data):
	before = _settings()
	client = as_user(factories.admin(3))

	with db_diff() as d:
		r = client.post(f"/admin/site_settings/{quote(setting)}", data, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()
	assert _settings() == before


def test_an_unknown_setting_is_not_found():
	before = _settings()
	client = as_user(factories.admin(3))

	with db_diff() as d:
		r = client.post(f"/admin/site_settings/{factories.unique('setting')}", headers=XHR)

	assert_status(r, 404)
	d.assert_exactly()
	assert _settings() == before
