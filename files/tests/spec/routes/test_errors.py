'''
How a refusal is answered, whatever refuses: a browser gets a page; a script's request (an "xhr" header) and anything with an Authorization header, whether or not it names a token, get JSON: {"code": the status, "error": its name, "description": what it means, "details": what this refusal says, or null}.
'''
import pytest

from files.tests.spec.harness import *


def test_a_browser_gets_a_page():
	assert_html(anon().get(f"/{factories.unique()}"), 404)


@pytest.mark.parametrize("client", ["script", "a token naming nothing"])
def test_a_script_and_an_authorization_header_get_json(client):
	headers = XHR if client == "script" else {"Authorization": factories.unique("token")}

	r = anon().get(f"/{factories.unique()}", headers=headers)

	assert_status(r, 404)
	assert r.header("Content-Type").startswith("application/json")
	assert r.json == {"code": 404, "error": ANY, "description": ANY, "details": None}
