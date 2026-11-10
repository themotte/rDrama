'''
The front page (GET /, not other pages built like it such as /catalog) carries a tip for phone browsers about installing the site as an app: the element with id "mobile-prompt". It isn't offered inside apps' web views (user agents containing "; wv) ").

POST /dismiss_mobile_tip (no form key needed, and allowed in read-only mode since it only changes the browser's own session) answers 204 and records the time in the session as "tooltip_last_dismissed" (epoch seconds). The front page then leaves the tip out for 30 days after that time.
'''
import time

import pytest

from files.tests.spec.harness import *

DAY = 86400
WEBVIEW_UA = "Mozilla/5.0 (Linux; Android 14; Pixel 8 Build/AP2A; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/126.0 Mobile Safari/537.36"


@pytest.mark.parametrize("client", [anon, lambda: as_user(factories.user())], ids=["visitor", "user"])
def test_the_front_page_offers_the_tip(client):
	assert has_element(client().get("/"), "mobile-prompt")


def test_other_pages_dont_offer_it():
	assert not has_element(anon().get("/catalog"), "mobile-prompt")


def test_web_views_arent_offered_it():
	assert not has_element(anon().get("/", headers={"User-Agent": WEBVIEW_UA}), "mobile-prompt")


@pytest.mark.parametrize("read_only", [False, True], ids=["normally", "in read-only mode"])
def test_dismissing_records_the_time_in_the_session(read_only):
	site_settings_set("Read-only mode", read_only)
	client = as_user(factories.user())
	before = int(time.time())

	r = client.post_raw("/dismiss_mobile_tip")

	assert_status(r, 204)
	assert before <= client.session()["tooltip_last_dismissed"] <= int(time.time())
	assert not has_element(client.get("/"), "mobile-prompt")


@pytest.mark.parametrize("days_ago, offered", [(29, False), (31, True)])
def test_the_tip_returns_30_days_after_dismissal(days_ago, offered):
	client = anon()
	client.get("/")
	client.session_update(tooltip_last_dismissed=int(time.time()) - days_ago * DAY)

	r = client.get("/")

	assert has_element(r, "mobile-prompt") == offered
