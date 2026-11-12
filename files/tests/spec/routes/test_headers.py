'''
Headers every response carries, whatever answered it (a page, JSON, a file, an error, a redirect, or a refusal before any route):
- Content-Security-Policy: at least the directives in CSP, each allowing at most the sources listed there, compared as written (fewer is fine), with "object-src 'none'". Further directives, which can only restrict, are allowed.
- Strict-Transport-Security: max-age=31536000
- X-Frame-Options: deny
'''
import pytest

from files.tests.spec.harness import *

CSP = {
	"script-src": {"'self'", "'unsafe-inline'", "https://*.googletagmanager.com", "https://hcaptcha.com", "https://*.hcaptcha.com"},
	"img-src": {"'self'", "https://*.google-analytics.com", "https://*.googletagmanager.com"},
	"connect-src": {"'self'", "https://*.google-analytics.com", "https://*.analytics.google.com", "https://*.googletagmanager.com", "https://hcaptcha.com", "https://*.hcaptcha.com"},
	"object-src": {"'none'"},
	"frame-src": {"https://hcaptcha.com", "https://*.hcaptcha.com"},
	"style-src": {"'self'", "'unsafe-inline'", "https://hcaptcha.com", "https://*.hcaptcha.com"},
}


def _page():
	return anon().get("/")


def _json():
	return as_api(factories.api_token(factories.user())).get(f"/post/{factories.post(factories.user())['id']}")


def _file():
	return anon().get(DEFAULT_PICTURE)


def _not_found():
	return anon().get(f"/{factories.unique('nowhere')}")


def _redirect():
	return as_user(factories.user()).get("/me")


def _other_host():
	return anon().get("/", headers={"Host": "elsewhere.example"})


def _no_user_agent():
	return anon().get("/", headers={"User-Agent": ""})


RESPONSES = {"page": (_page, 200), "json": (_json, 200), "file": (_file, 200), "not found": (_not_found, 404), "redirect": (_redirect, 302), "other host": (_other_host, 403), "no user agent": (_no_user_agent, 403)}


def _policy(header):
	directives = {}
	for directive in header.split(";"):
		if directive.strip():
			name, *sources = directive.split()
			directives[name] = set(sources)
	return directives


@pytest.fixture(params=RESPONSES, ids=list(RESPONSES))
def response(request):
	make, status = RESPONSES[request.param]
	r = make()
	assert_status(r, status)
	return r


def test_every_response_carries_the_content_security_policy(response):
	[header] = response.header_all("Content-Security-Policy")
	policy = _policy(header)

	assert CSP.keys() <= policy.keys()
	assert {name: policy[name] - sources for name, sources in CSP.items()} == {name: set() for name in CSP}
	assert policy["object-src"] == {"'none'"}


def test_every_response_asks_browsers_to_keep_to_https(response):
	assert response.header_all("Strict-Transport-Security") == ["max-age=31536000"]


def test_every_response_refuses_to_be_framed(response):
	assert response.header_all("X-Frame-Options") == ["deny"]
