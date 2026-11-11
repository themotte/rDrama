'''
The spec's limit table (files/tests/spec/harness/limits.py) gives each route the limits the site gives it, and the site's default, site-wide and crawler limits and crawler rule. All of its limits hold the site to it, also those too large for the spec's tests to reach.
'''
import pytest

from files.__main__ import app, is_known_bot, limiter
from files.helpers import rate_limits
from files.tests import route_table
from files.tests.spec.harness import limits
from files.tests.spec.harness.routes import ROUTES

_APP_ROUTES = route_table.app_routes(app)
_ROWS = [(r.method, r.path) for r in ROUTES]


def test_the_table_names_only_rows_of_the_route_table():
	assert set(limits.OWN) | limits.EXEMPT <= set(_ROWS)
	assert not set(limits.OWN) & limits.EXEMPT


def test_the_table_is_sorted_like_the_route_table():
	assert list(limits.OWN) == sorted(limits.OWN, key=_ROWS.index)


@pytest.mark.parametrize("row", _ROWS, ids=lambda row: f"{row[0]} {row[1]}")
def test_each_rows_limits_are_its_views(row):
	marked = getattr(_APP_ROUTES[row], "rate_limits", None)
	listed = () if row in limits.EXEMPT else rate_limits.parse(limits.OWN[row]) if row in limits.OWN else None

	assert marked == listed


def test_the_sites_own_limits_are_the_tables():
	assert (limiter._default, limiter._site_wide, limiter._crawlers) == tuple(rate_limits.parse(text) for text in (limits.DEFAULT, limits.SITE_WIDE, limits.CRAWLERS))


@pytest.mark.parametrize("user_agent", [
	"Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
	"Mozilla/5.0 (compatible; Bytespider; spider-feedback@bytedance.com)",
	"Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ChatGPT-User/1.0",
	"ROBOT",
	"Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
	"curl/8.0",
])
def test_the_site_knows_crawlers_by_the_tables_rule(user_agent):
	with app.test_request_context(headers={"User-Agent": user_agent}):
		assert is_known_bot() == limits.is_crawler(user_agent)
