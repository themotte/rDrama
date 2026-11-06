'''
POST /settings/profile, preference fields.

A request applies at most one "single-choice" field. Single-choice fields are considered in this order: hidevotedon, cardview, highlightcomments, newtab, newtabexternal, over18, nofollow (each whenever present), then the text fields (see test_profile_text), which end the request. Otherwise every present "multi" field applies too: frontsize, defaultsortingcomments, defaultsorting, theme.

Success is a JSON message. A request that changes nothing is a 400. A request with an unlisted multi-field value (400) changes nothing at all.
'''
import pytest

from files.tests.spec.harness import *

BOOLEAN_TOGGLES = [
	("hidevotedon", "hidevotedon"),
	("cardview", "cardview"),
	("highlightcomments", "highlightcomments"),
	("newtab", "newtab"),
	("newtabexternal", "newtabexternal"),
	("over18", "over_18"),
	("nofollow", "is_nofollow"),
]


def _post(user, data, headers=None):
	return as_user(user).post("/settings/profile", data, headers=headers)


@pytest.mark.parametrize("param, column", BOOLEAN_TOGGLES)
@pytest.mark.parametrize("value, stored", [("true", True), ("false", False), ("yes", False)])
def test_boolean_toggle_stores_whether_value_is_true(param, column, value, stored):
	u = factories.user(**{column: not stored})

	with db_diff() as d:
		r = _post(u, {param: value})

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {column: stored}}})


@pytest.mark.parametrize("param, column", BOOLEAN_TOGGLES)
def test_boolean_toggle_to_the_current_value_succeeds_without_change(param, column):
	u = factories.user(**{column: False})

	with db_diff() as d:
		r = _post(u, {param: "false"})

	assert_json_message(r)
	d.assert_exactly()


def test_only_the_first_single_choice_field_applies():
	u = factories.user(hidevotedon=False, cardview=False, newtab=False)

	with db_diff() as d:
		r = _post(u, {"newtab": "true", "cardview": "true", "hidevotedon": "true"})

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {"hidevotedon": True}}})


def test_single_choice_field_combines_with_multi_fields():
	u = factories.user(cardview=False)

	with db_diff() as d:
		r = _post(u, {"cardview": "true", "frontsize": "50", "defaultsorting": "old"})

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {"cardview": True, "frontsize": 50, "defaultsorting": "old"}}})


def test_nothing_to_change_is_rejected():
	u = factories.user()

	with db_diff() as d:
		r = _post(u, {}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


def test_a_rejected_field_discards_the_whole_request():
	u = factories.user(cardview=False, defaultsorting="new")

	with db_diff() as d:
		r = _post(u, {"cardview": "true", "defaultsorting": "old", "frontsize": "bogus"}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


@pytest.mark.parametrize("value", ["15", "25", "50", "100"])
def test_frontsize_accepts_listed_sizes(value):
	u = factories.user(frontsize=25 if value != "25" else 50)

	with db_diff() as d:
		r = _post(u, {"frontsize": value})

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {"frontsize": int(value)}}})


@pytest.mark.parametrize("field", ["frontsize", "defaultsortingcomments", "defaultsorting", "theme"])
def test_multi_field_rejects_unlisted_values(field):
	u = factories.user()

	with db_diff() as d:
		r = _post(u, {field: "bogus"}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


@pytest.mark.parametrize("value", ["top", "bottom", "new", "old", "controversial", "comments"])
def test_default_comment_sort_accepts_comment_sorts(value):
	u = factories.user(defaultsortingcomments="hot")

	with db_diff() as d:
		r = _post(u, {"defaultsortingcomments": value})

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {"defaultsortingcomments": value}}})


def test_default_comment_sort_rejects_post_only_sorts():
	assert_status(_post(factories.user(), {"defaultsortingcomments": "hot"}, headers=XHR), 400)


@pytest.mark.parametrize("value", ["hot", "top", "bottom", "new", "old", "controversial", "comments"])
def test_default_post_sort_accepts_post_sorts(value):
	u = factories.user(defaultsorting="x")

	with db_diff() as d:
		r = _post(u, {"defaultsorting": value})

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {"defaultsorting": value}}})


@pytest.mark.parametrize("theme", ["TheMotte", "dramblr", "reddit", "dark", "light", "coffee", "tron", "4chan", "midnight"])
def test_theme_change_resets_theme_color_to_white(theme):
	u = factories.user(theme="x", themecolor="123456")

	with db_diff() as d:
		r = _post(u, {"theme": theme})

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {"theme": theme, "themecolor": "fff"}}})


def test_win98_theme_gets_its_own_color():
	u = factories.user(theme="x", themecolor="123456")

	with db_diff() as d:
		r = _post(u, {"theme": "win98"})

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {"theme": "win98", "themecolor": "30409f"}}})
