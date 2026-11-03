'''The request logs (perf and slow-request lines, the worker-timeout dump, gunicorn's access log) never record passwords, 2FA codes or signed tokens, and record everything else as sent, whatever the request holds.'''
import sys
from datetime import timedelta
from types import SimpleNamespace
from urllib.parse import quote_plus

import pytest
from gunicorn.config import Config

import files.__main__ as main
import files.routes.allroutes  # noqa: F401  (the module, not the route function of the same package name)
import gunicorn_config
from files.tests.spec.harness import anon, assert_status

SECRET_FIELDS = {"password": "v01q", "password_confirm": "v02q", "confirm_password": "v03q", "new_password": "v04q", "cnf_password": "v05q", "old_password": "v06q", "2fa_token": "v07q", "hash": "v08q", "h-captcha-response": "v09q", "formkey": "v10q", "secret": "v11q", "twofactor": "v12q", "2fa_remove": "v16q", "token": "v17q", "2fa_secret": "v18q"}
SECRET_VALUES = [*SECRET_FIELDS.values(), "v13q", "v14q", "v15q", "v19q", "v20q", "v21q"]
# A query token, a login return address carrying a verification link's token, the 2FA setup QR code's seed in the path, a percent-encoded parameter name, a question mark encoded in the path, and an encoded QR code path.
URLS = ["/login?id=5&token=v13q", "/login?redirect=%2Factivate%3Femail%3Da%2540b.c%26id%3D5%26token%3Dv14q", "/2faqr/v15q", "/login?%74oken=v19q", "/x%3Fa=/?token=v20q", "/%32faqr/v21q"]
# Values that look like URLs or carry question marks but are ordinary input.
ODD_VALUES = ["//[?", "http://[foo]?a=b", "Is it? Yes", "a?a=" * 100, "%zz?%"]


def _leaks(text):
	return [value for value in SECRET_VALUES if value in text]


@pytest.fixture
def perf_log(monkeypatch):
	recorded = []
	monkeypatch.setattr(main._perf, "record_http", lambda elapsed, detail, agent: recorded.append(detail))
	monkeypatch.setattr(main, "SLOW_THRESHOLD", 0)
	monkeypatch.setattr(main.app, "debug", False)
	return recorded


@pytest.fixture
def access_log(tmp_path):
	'''Writes one access-log line the way gunicorn does, with this site's format and logger, and returns the log so far.'''
	config = Config()
	config.set("logger_class", gunicorn_config.logger_class)
	config.set("accesslog", str(tmp_path / "access.log"))
	config.set("access_log_format", gunicorn_config.access_log_format)
	logger = config.logger_class(config)

	def write(url, referer):
		environ = {"REQUEST_METHOD": "GET", "RAW_URI": url, "SERVER_PROTOCOL": "HTTP/1.1", "PATH_INFO": url.split("?")[0], "QUERY_STRING": url.partition("?")[2], "HTTP_REFERER": referer}
		logger.access(SimpleNamespace(status="200 OK", headers=[], sent=0), SimpleNamespace(headers=[("Referer", referer), ("X-Real-IP", "192.0.2.1")]), environ, timedelta(0))
		return (tmp_path / "access.log").read_text()

	return write


@pytest.mark.parametrize("url", URLS)
def test_perf_and_slow_request_lines_redact_secrets(perf_log, capsys, url):
	anon().post_raw(url, {**SECRET_FIELDS, "title": "kept"})

	[detail] = perf_log
	slow = capsys.readouterr().err
	assert _leaks(detail) == [] and _leaks(slow) == [], (detail, slow)
	assert "'title': 'kept'" in detail and "[slow-request]" in slow


def test_a_return_address_on_the_login_form_is_redacted(perf_log):
	anon().post_raw("/login", {"username": "nobody", "redirect": "/activate?email=a%40b.c&id=5&token=v14q"})

	assert _leaks(perf_log[0]) == [], perf_log[0]


def test_ordinary_queries_are_logged_as_sent(perf_log):
	anon().get("/search/posts/?q=what%3F+now&sort=new&flag&token")

	assert perf_log == ["GET /search/posts/?q=what%3F+now&sort=new&flag&token"]


def test_an_ordinary_login_return_address_is_logged_as_sent(perf_log):
	anon().get("/login?redirect=%2Fpost%2F5%3Fsort%3Dnew%26page%3D2")
	anon().post_raw("/login", {"username": "nobody", "redirect": "/post/5?sort=new&page=2"})

	assert perf_log == ["GET /login?redirect=%2Fpost%2F5%3Fsort%3Dnew%26page%3D2", "POST /login? form={'username': 'nobody', 'redirect': '/post/5?sort=new&page=2'}"]


def test_huge_forms_are_logged_cut_short(perf_log):
	anon().post_raw("/login", {"redirect": "?" + "&" * 2_000_000, **{f"field{i}": "x" * 100_000 for i in range(5)}})
	anon().post_raw("/login", {f"field{i}": "x" for i in range(5000)})

	assert [len(detail) < 20_000 for detail in perf_log] == [True, True], [len(detail) for detail in perf_log]


@pytest.mark.parametrize("value", ODD_VALUES)
def test_odd_query_values_neither_fail_the_request_nor_change_in_the_log(perf_log, value):
	r = anon().get(f"/?q={quote_plus(value)}")

	assert_status(r, 200)
	assert perf_log == [f"GET /?q={quote_plus(value)}"]


@pytest.mark.parametrize("value", ODD_VALUES)
def test_odd_form_values_are_logged_as_sent(perf_log, value):
	anon().post_raw("/login", {"username": value})

	assert perf_log == [f"POST /login? form={ {'username': value} }"]


@pytest.mark.parametrize("url", URLS)
def test_the_worker_timeout_dump_redacts_secrets(monkeypatch, url):
	class Recording(dict):
		seen = []

		def __setitem__(self, key, value):
			Recording.seen.append(value)
			super().__setitem__(key, value)

	monkeypatch.setattr(sys.modules["files.routes.allroutes"], "active_requests", Recording())

	anon().get(url)

	[(method, path, _)] = Recording.seen
	assert _leaks(path) == [], path


@pytest.mark.parametrize("url", URLS)
def test_the_access_log_redacts_the_request_line_and_referer(access_log, url):
	line = access_log(url, f"https://example.com{url}")

	assert "192.0.2.1" in line and _leaks(line) == [], line


@pytest.mark.parametrize("value", ODD_VALUES)
def test_odd_request_lines_and_referers_are_logged_as_sent(access_log, value):
	uri = f"/search/posts/?q={value.replace(' ', '+')}"

	line = access_log(uri, value)

	assert line.count("192.0.2.1") == 1 and f'"GET {uri} HTTP/1.1"' in line and f'"{value}"' in line, line
