'''
Account identity settings: username, flair title, colors, custom filter words, changelog subscription.
'''
import pytest

from files.tests.spec.harness import *


# Username

def test_username_change():
	u = factories.user()
	new_name = factories.unique("renamed")

	with db_diff() as d:
		r = as_user(u).post("/settings/name_change", {"name": f" {new_name} "})

	assert_redirect(r, "/settings/profile")
	d.assert_exactly(updated={"users": {u["id"]: {"username": new_name}}})


def test_username_change_keeps_the_original_username():
	u = factories.user()

	as_user(u).post("/settings/name_change", {"name": factories.unique("renamed")})

	assert db.row("users", id=u["id"])["original_username"] == u["original_username"]


def test_username_change_may_change_only_capitalization():
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).post("/settings/name_change", {"name": u["username"].upper()})

	assert_redirect(r, "/settings/profile")
	d.assert_exactly(updated={"users": {u["id"]: {"username": u["username"].upper()}}})


@pytest.mark.parametrize("taken_column", ["username", "original_username"])
def test_username_change_refuses_names_in_use_case_insensitively(taken_column):
	taken = factories.unique("taken")
	factories.user(**{taken_column: taken})
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).post("/settings/name_change", {"name": taken.upper()})

	assert_html(r, 200)
	d.assert_exactly()


@pytest.mark.parametrize("name", ["ab", "x" * 26, "has space", "bad!char", ""])
def test_username_change_refuses_invalid_names(name):
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).post("/settings/name_change", {"name": name})

	assert_html(r, 200)
	d.assert_exactly()


@pytest.mark.parametrize("name", ["abc", "x" * 25, "with-dash_and_underscore"])
def test_username_change_accepts_valid_names(name):
	u = factories.user()

	assert_redirect(as_user(u).post("/settings/name_change", {"name": name}), "/settings/profile")


def test_username_change_to_the_same_name_changes_nothing():
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).post("/settings/name_change", {"name": u["username"]})

	assert_html(r, 200)
	d.assert_exactly()


def test_username_change_without_a_name_is_rejected():
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).post("/settings/name_change", {}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


def test_permanently_banned_users_cannot_change_username():
	u = factories.user(is_banned=1, unban_utc=0)

	with db_diff() as d:
		r = as_user(u).post("/settings/name_change", {"name": factories.unique("renamed")}, headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


def test_temporarily_banned_users_can_change_username():
	u = factories.user(is_banned=1, unban_utc=2_000_000_000)

	assert_redirect(as_user(u).post("/settings/name_change", {"name": factories.unique("renamed")}), "/settings/profile")


# Flair title

def test_title_change_stores_plain_and_rendered_title():
	u = factories.user()
	token = factories.unique()

	with db_diff() as d:
		r = as_user(u).post("/settings/title_change", {"title": f" {token} <b>bold</b> "})

	assert_redirect(r, "/settings/profile")
	d.assert_exactly(updated={"users": {u["id"]: {"customtitleplain": f"{token} <b>bold</b>", "customtitle": ANY}}})
	rendered = db.row("users", id=u["id"])["customtitle"]
	assert token in rendered and "<b>" not in rendered


def test_title_is_truncated_to_100_characters_and_drops_the_forbidden_glyph():
	u = factories.user()

	with db_diff() as d:
		as_user(u).post("/settings/title_change", {"title": "𒐪" + "a" * 120})

	d.assert_exactly(updated={"users": {u["id"]: {"customtitleplain": "a" * 99, "customtitle": ANY}}})


def test_locked_flair_cannot_be_changed():
	u = factories.user(flairchanged=2_000_000_000)

	with db_diff() as d:
		r = as_user(u).post("/settings/title_change", {"title": "new"}, headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


def test_title_change_without_a_title_is_rejected():
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).post("/settings/title_change", {}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


# Colors

@pytest.mark.parametrize("path, field, column", [
	("/settings/namecolor", "color", "namecolor"),
	("/settings/themecolor", "themecolor", "themecolor"),
	("/settings/titlecolor", "titlecolor", "titlecolor"),
	("/settings/verifiedcolor", "verifiedcolor", "verifiedcolor"),
])
class TestColor:
	def test_six_character_value_is_stored_without_leading_hash(self, path, field, column):
		u = factories.user()

		with db_diff() as d:
			r = as_user(u).post(path, {field: " #a1b2c3 "})

		assert_redirect(r, "/settings/profile")
		d.assert_exactly(updated={"users": {u["id"]: {column: "a1b2c3"}}})

	@pytest.mark.parametrize("value", ["", "#abc", "abcdefa"])
	def test_other_lengths_are_refused(self, path, field, column, value):
		u = factories.user()

		with db_diff() as d:
			r = as_user(u).post(path, {field: value})

		assert_html(r, 200)
		d.assert_exactly()


# Custom filter words

def test_filter_words_are_stored_truncated_then_trimmed():
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).post("/settings/filters", {"filters": "x" * 999 + " " * 10})

	assert_html(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {"custom_filter_list": "x" * 999}}})


def test_filter_words_are_truncated_to_1000_characters():
	u = factories.user()

	with db_diff() as d:
		as_user(u).post("/settings/filters", {"filters": "x" * 1100})

	d.assert_exactly(updated={"users": {u["id"]: {"custom_filter_list": "x" * 1000}}})


def test_filter_words_unchanged_changes_nothing():
	u = factories.user(custom_filter_list="a,b")

	with db_diff() as d:
		r = as_user(u).post("/settings/filters", {"filters": " a,b "})

	assert_html(r, 200)
	d.assert_exactly()


def test_filter_words_without_the_field_are_rejected():
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).post("/settings/filters", {}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


# Changelog subscription

@pytest.mark.parametrize("before", [False, True])
def test_changelog_subscription_toggles(before):
	u = factories.user(changelogsub=before)

	with db_diff() as d:
		r = as_user(u).post("/changelogsub")

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {"changelogsub": not before}}})
