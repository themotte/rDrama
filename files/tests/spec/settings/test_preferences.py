'''
POST /settings/profile, preference fields.

A request applies at most one "single-choice" field. Single-choice fields are considered in this order: reddit (only when different from the current value), hidevotedon, cardview, highlightcomments, newtab, newtabexternal, nitter, controversial, over18, nofollow (each whenever present), then the text fields (see test_profile_text), which end the request. Otherwise every present "multi" field applies too: frontsize, defaultsortingcomments, defaultsorting, defaulttime, theme, house.

Success is a JSON message. A request that changes nothing is a 400. A request with an unlisted multi-field value (400) or an unaffordable house (403) changes nothing at all.
'''
import pytest

from files.tests.spec.harness import *

BOOLEAN_TOGGLES = [
	("hidevotedon", "hidevotedon"),
	("cardview", "cardview"),
	("highlightcomments", "highlightcomments"),
	("newtab", "newtab"),
	("newtabexternal", "newtabexternal"),
	("nitter", "nitter"),
	("controversial", "controversial"),
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


@pytest.mark.parametrize("site", ["old.reddit.com", "reddit.com", "i.reddit.com", "teddit.net", "libredd.it", "unddit.com"])
def test_reddit_frontend_accepts_known_sites(site):
	u = factories.user(reddit="old.reddit.com" if site != "old.reddit.com" else "reddit.com")

	with db_diff() as d:
		r = _post(u, {"reddit": site})

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {"reddit": site}}})


def test_reddit_frontend_rejects_unknown_site():
	u = factories.user()

	with db_diff() as d:
		r = _post(u, {"reddit": "evil.example"}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


def test_unknown_reddit_frontend_still_ends_the_single_choice_fields():
	u = factories.user(cardview=False)

	with db_diff() as d:
		r = _post(u, {"reddit": "evil.example", "cardview": "true", "frontsize": "50"})

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {"frontsize": 50}}})


def test_reddit_frontend_equal_to_the_current_one_falls_through_to_later_fields():
	u = factories.user(reddit="reddit.com", cardview=False)

	with db_diff() as d:
		r = _post(u, {"reddit": "reddit.com", "cardview": "true"})

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {"cardview": True}}})


def test_reddit_frontend_equal_to_the_current_one_alone_changes_nothing():
	u = factories.user(reddit="reddit.com")

	assert_status(_post(u, {"reddit": "reddit.com"}, headers=XHR), 400)


def test_only_the_first_single_choice_field_applies():
	u = factories.user(reddit="old.reddit.com", cardview=False, newtab=False)

	with db_diff() as d:
		r = _post(u, {"newtab": "true", "cardview": "true", "reddit": "reddit.com"})

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {"reddit": "reddit.com"}}})


def test_single_choice_field_combines_with_multi_fields():
	u = factories.user(cardview=False)

	with db_diff() as d:
		r = _post(u, {"cardview": "true", "frontsize": "50", "defaulttime": "week"})

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {"cardview": True, "frontsize": 50, "defaulttime": "week"}}})


def test_nothing_to_change_is_rejected():
	u = factories.user()

	with db_diff() as d:
		r = _post(u, {}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


@pytest.mark.parametrize("bad, status", [({"frontsize": "bogus"}, 400), ({"house": "Furry"}, 403)])
def test_a_rejected_field_discards_the_whole_request(bad, status):
	u = factories.user(cardview=False, defaulttime="all", coins=0, procoins=0, house=None)

	with db_diff() as d:
		r = _post(u, {"cardview": "true", "defaulttime": "week", **bad}, headers=XHR)

	assert_status(r, status)
	d.assert_exactly()


@pytest.mark.parametrize("value", ["15", "25", "50", "100"])
def test_frontsize_accepts_listed_sizes(value):
	u = factories.user(frontsize=25 if value != "25" else 50)

	with db_diff() as d:
		r = _post(u, {"frontsize": value})

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {"frontsize": int(value)}}})


@pytest.mark.parametrize("field", ["frontsize", "defaultsortingcomments", "defaultsorting", "defaulttime", "theme"])
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


@pytest.mark.parametrize("value", ["hot", "bump", "top", "bottom", "new", "old", "controversial", "comments"])
def test_default_post_sort_accepts_post_sorts(value):
	u = factories.user(defaultsorting="x")

	with db_diff() as d:
		r = _post(u, {"defaultsorting": value})

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {"defaultsorting": value}}})


@pytest.mark.parametrize("value", ["hour", "day", "week", "month", "year", "all"])
def test_default_time_filter_accepts_listed_windows(value):
	u = factories.user(defaulttime="x")

	with db_diff() as d:
		r = _post(u, {"defaulttime": value})

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {"defaulttime": value}}})


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


# Houses

@pytest.mark.parametrize("house", ["Furry", "Femboy", "Vampire", "Racist"])
def test_joining_a_first_house_costs_500_coins(house):
	u = factories.user(coins=600, house=None)

	with db_diff() as d:
		r = _post(u, {"house": house})

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {"house": house, "coins": 100}}})


def test_switching_houses_costs_2000_coins():
	u = factories.user(coins=2500, house="Furry")

	with db_diff() as d:
		r = _post(u, {"house": "Vampire"})

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {"house": "Vampire", "coins": 500}}})


def test_leaving_a_house_costs_2000_coins():
	u = factories.user(coins=2000, house="Furry")

	with db_diff() as d:
		r = _post(u, {"house": "None"})

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {"house": None, "coins": 0}}})


def test_house_is_paid_from_marseybux_when_coins_fall_short():
	u = factories.user(coins=100, procoins=500, house=None)

	with db_diff() as d:
		r = _post(u, {"house": "Furry"})

	assert_json_message(r)
	d.assert_exactly(updated={"users": {u["id"]: {"house": "Furry", "procoins": 0}}})


def test_house_is_refused_when_neither_currency_covers_it():
	u = factories.user(coins=499, procoins=499, house=None)

	with db_diff() as d:
		r = _post(u, {"house": "Furry"}, headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


def test_unlisted_house_is_ignored():
	u = factories.user(coins=1000)

	with db_diff() as d:
		r = _post(u, {"house": "Gryffindor"}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()
