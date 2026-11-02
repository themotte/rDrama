'''
Custom CSS: POST /settings/css (field "css", applied to the site for the user themselves) and POST /settings/profilecss (field "profilecss", applied to their profile page for everyone).

Stored with backslashes removed, CRLF normalized, surrounding whitespace trimmed, and truncated to 4000 characters. CSS able to load outside resources or break out of its style block is refused.
'''
import pytest

from files.tests.spec.harness import *

ENDPOINTS = [("/settings/css", "css"), ("/settings/profilecss", "profilecss")]


@pytest.mark.parametrize("path, field", ENDPOINTS)
def test_css_is_stored_trimmed_without_backslashes(path, field):
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).post(path, {field: " body {\r\n color: red\\; }\r\n"})

	assert_html(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {field: "body {\n color: red; }"}}})


@pytest.mark.parametrize("path, field", ENDPOINTS)
def test_css_is_truncated_to_4000_characters(path, field):
	u = factories.user()

	with db_diff() as d:
		as_user(u).post(path, {field: "a" * 4100})

	d.assert_exactly(updated={"users": {u["id"]: {field: "a" * 4000}}})


@pytest.mark.parametrize("path, field", ENDPOINTS)
@pytest.mark.parametrize("css", [
	"</style><script>",
	"@import 'x.css';",
	"body { background: url(https://example.com/x.png) }",
	"a { b: URL( 'x' ) }",
	"body { background: image-set('https://example.com/x.png' 1x) }",
	"body { background: -webkit-image-set('https://example.com/x.png' 1x) }",
])
def test_dangerous_css_is_refused(path, field, css):
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).post(path, {field: css}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


@pytest.mark.parametrize("path, field", ENDPOINTS)
def test_empty_css_clears_it(path, field):
	u = factories.user(**{field: "body {}"})

	with db_diff() as d:
		r = as_user(u).post(path, {})

	assert_html(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {field: ""}}})


@pytest.mark.parametrize("path, field", ENDPOINTS)
def test_css_page_shows_the_current_css(path, field):
	token = factories.unique()
	u = factories.user(**{field: f".{token} {{}}"})

	assert_in_payload(as_user(u).get(path), token)
