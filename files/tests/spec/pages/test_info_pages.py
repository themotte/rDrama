'''
The site's fixed pages, open to everyone: GET /sidebar, /rules, /support and /formatting (the guide to writing posts and comments).

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
