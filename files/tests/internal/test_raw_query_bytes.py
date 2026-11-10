'''A query string carrying bytes that aren't UTF-8 (which a client can send raw, and the server passes on) gets 400 like any other malformed request. The spec's client only sends well-formed URLs, so this lives here.'''
import files.__main__ as main


def _get(query_string):
	return main.app.test_client().get("/", environ_overrides={"QUERY_STRING": query_string}, headers={"Host": main.app.config["SERVER_NAME"], "User-Agent": "test"})


def test_a_query_that_is_not_utf8_is_refused():
	r = _get("q=\xe9")

	assert r.status_code == 400
	# With the headers every response carries (spec/routes/test_headers.py)
	assert all(r.headers.get(name) for name in ("Content-Security-Policy", "Strict-Transport-Security", "X-Frame-Options"))


def test_percent_escapes_that_are_not_utf8_are_still_served():
	assert _get("q=%E9").status_code == 200
