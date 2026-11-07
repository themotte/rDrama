'''
GET /api is the guide to the API (obtaining apps and tokens, and using them), open to everyone.
'''
import pytest

from files.tests.spec.harness import *


@pytest.mark.parametrize("client", [anon, lambda: as_user(factories.user())], ids=["visitor", "user"])
def test_the_guide_is_open_to_everyone(client):
	assert_html(client().get("/api"), 200)
