'''
The site's fixed pages.

/logged_out, which once redirected to the path after it, is gone: its addresses are 404 like any unknown page.
'''
import pytest

from files.tests.spec.harness import *


@pytest.mark.parametrize("path", ["/logged_out", "/logged_out/", "/logged_out/settings/profile"])
def test_logged_out_addresses_are_not_found(path):
	assert_status(anon().get(path), 404)
