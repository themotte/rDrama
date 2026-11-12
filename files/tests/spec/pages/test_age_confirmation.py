'''
Confirming age: POST /allow_nsfw waives the 18+ notice for the browser for an hour (the session's "over_18", harness/session.py), with or without an account, and sends it on to "redir": a path on the site, or the site's own address, is followed; anything else (none, empty, another site) goes to the front page. A path starting with "//" is taken as a path on the site too.
'''
import time

import pytest

from files.tests.spec.harness import *

HOUR = 3600


@pytest.mark.parametrize("data", [{}, {"redir": ""}, {"redir": "https://other.example/page"}, {"redir": "other.example/page"}, {"redir": config.site_url()}], ids=["none", "empty", "another site", "no leading slash", "the bare site address"])
def test_without_a_page_on_the_site_it_goes_to_the_front_page(data):
	assert_redirect(anon().post("/allow_nsfw", data), "/")


@pytest.mark.parametrize("redir", ["/rules", "/rules?a=1", "//other.example/page"], ids=["a path", "a path with a query", "a path starting with //"])
def test_a_path_on_the_site_is_followed(redir):
	assert_redirect(anon().post("/allow_nsfw", {"redir": redir}), redir.split("?")[0])


def test_the_sites_own_address_is_followed():
	assert_redirect(anon().post("/allow_nsfw", {"redir": f"{config.site_url()}/rules"}), "/rules")


@pytest.mark.parametrize("viewer", ["visitor", "member"])
def test_the_notice_is_waived_for_an_hour(viewer):
	client = anon() if viewer == "visitor" else as_user(factories.user(over_18=False))
	before = int(time.time())

	assert_redirect(client.post("/allow_nsfw"), "/")

	assert before + HOUR <= client.session()["over_18"] <= int(time.time()) + HOUR


@pytest.mark.parametrize("seconds, shown", [(-1, False), (60, True)], ids=["passed", "still running"])
def test_a_waiver_holds_until_its_time(seconds, shown):
	body = factories.unique("body")
	post = factories.post(factories.user(), body=body, over_18=True)
	client = anon().session_update(over_18=int(time.time()) + seconds)

	r = client.get(f"/post/{post['id']}")

	assert_html(r, 200)
	(assert_in_payload if shown else assert_not_in_payload)(r, body)
