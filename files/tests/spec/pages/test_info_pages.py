'''
The site's fixed pages, open to everyone: GET /sidebar, /rules, /support and /formatting (the guide to writing posts and comments).

The rules are cited by anchor (/rules#<anchor>, markup.RULE_ANCHORS): /rules keeps an element with each of those ids, and the sidebar's links to the rules use them.

/logged_out, which once redirected to the path after it, is gone: its addresses are 404 like any unknown page.
'''
import pytest

from files.tests.spec.harness import *


@pytest.mark.parametrize("path", ["/logged_out", "/logged_out/", "/logged_out/settings/profile"])
def test_logged_out_addresses_are_not_found(path):
	assert_status(anon().get(path), 404)


@pytest.mark.parametrize("client", [anon, lambda: as_user(factories.user()), lambda: as_api(factories.api_token(factories.user()))], ids=["visitor", "user", "API client"])
@pytest.mark.parametrize("path", ["/sidebar", "/rules", "/support", "/formatting"])
def test_the_fixed_pages_are_open_to_everyone(path, client):
	assert_html(client().get(path), 200)


@pytest.mark.parametrize("anchor", markup.RULE_ANCHORS)
def test_the_rules_keep_their_anchors(anchor):
	assert has_element(anon().get("/rules"), anchor)


def test_the_sidebar_links_to_the_rules_by_their_anchors():
	anchors = [link.removeprefix("/rules#") for link in links(anon().get("/sidebar")) if link.startswith("/rules#")]
	assert anchors and set(anchors) <= set(markup.RULE_ANCHORS)
