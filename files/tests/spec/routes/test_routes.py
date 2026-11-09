'''
The route table (harness/routes.py, which says what each column means) holds for every route: each refusal a route's gate makes, checked with values that name nothing, since the gate answers first; the session every gate gives a browser; the methods each path takes.
'''
import re

import pytest

from files.tests.spec.harness import *
from files.tests.spec.harness.routes import ANYONE, PUBLIC, ROUTES, USER_NOT_PERMABANNED, admin_level

# An id no row has: the largest the id columns hold
_UNUSED_ID = str(2**31 - 1)


def _path(route) -> str:
	'''The route's path with every variable filled with a value that names nothing.'''
	def value(m):
		kind = m.group(1)
		if kind == "id": return _UNUSED_ID
		if kind in ("text", "path"): return "x"
		return kind.split("|")[0]
	return re.sub(r"<([^>]+)>", value, route.path)


def _id(route) -> str:
	return f"{route.method} {route.path}"


def _member_with_access(route) -> dict:
	level = admin_level(route.access)
	return factories.user() if level is None else factories.admin(level)


_GATED = [r for r in ROUTES if r.access not in (PUBLIC, ANYONE)]
_ADMIN = [r for r in ROUTES if admin_level(r.access) is not None]
_NOT_PERMABANNED = [r for r in ROUTES if r.access == USER_NOT_PERMABANNED]
_NO_API_CLIENTS = [r for r in ROUTES if not r.api_clients]
_PATHS = sorted({r.path for r in ROUTES})


@pytest.mark.parametrize("slash", ["", "/"], ids=["as written", "with a trailing slash"])
@pytest.mark.parametrize("route", _GATED, ids=_id)
def test_anonymous_requests_are_sent_to_log_in(route, slash):
	path = _path(route) + slash

	with db_diff() as d:
		r = anon().request(route.method, path)

	assert_login_redirect(r, returning_to=path)
	d.assert_exactly()


@pytest.mark.parametrize("route", [r for r in _GATED if r.method == "POST"], ids=_id)
def test_a_members_post_without_their_form_key_is_sent_to_log_in(route):
	path = _path(route)
	client = as_user(_member_with_access(route))

	with db_diff() as d:
		r = client.post_raw(path)

	assert_login_redirect(r, returning_to=path)
	d.assert_exactly()


@pytest.mark.parametrize("route", _ADMIN, ids=_id)
def test_members_below_the_admin_level_are_refused(route):
	client = as_user(factories.admin(admin_level(route.access) - 1))

	with db_diff() as d:
		r = client.request(route.method, _path(route)) if route.method == "GET" else client.post(_path(route))

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("route", _NOT_PERMABANNED, ids=_id)
def test_permanently_suspended_members_are_refused(route):
	client = as_user(factories.user(is_banned=factories.admin(2)["id"], unban_utc=0))

	with db_diff() as d:
		r = client.post(_path(route)) if route.method == "POST" else client.get(_path(route))

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("route", _NO_API_CLIENTS, ids=_id)
def test_api_clients_are_refused(route):
	client = as_api(factories.api_token(factories.admin(3)))

	with db_diff() as d:
		r = client.request(route.method, _path(route))

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("path, slash", [(p, s) for p in _PATHS for s in ("", "/") if not (p == "/" and s)], ids=lambda v: v or "as written")
def test_a_method_the_path_does_not_take_is_405(path, slash):
	methods = {r.method for r in ROUTES if r.path == path}
	unlisted = next(m for m in ("GET", "POST", "PUT") if m not in methods)
	route = next(r for r in ROUTES if r.path == path)

	with db_diff() as d:
		r = anon().request(unlisted, _path(route) + slash)

	assert_status(r, 405)
	d.assert_exactly()


def test_an_unlisted_path_is_404():
	assert_status(anon().get(f"/{factories.unique()}"), 404)


@pytest.mark.parametrize("route", [r for r in ROUTES if r.method == "GET"], ids=_id)
def test_head_is_answered_as_get_without_the_body(route):
	get, head = anon().get(_path(route)), anon().request("HEAD", _path(route))

	assert_status(head, get.status)
	assert head.body == b""


@pytest.mark.parametrize("path", _PATHS)
def test_options_lists_the_methods_a_path_takes(path):
	methods = {r.method for r in ROUTES if r.path == path}
	route = next(r for r in ROUTES if r.path == path)

	r = anon().request("OPTIONS", _path(route))

	assert_status(r, 200)
	assert {m.strip() for m in r.header("Allow").split(",")} == methods | {"OPTIONS"} | ({"HEAD"} if "GET" in methods else set())


def test_doubled_slashes_are_redirected_to_the_merged_path():
	post = factories.post(factories.user())

	r = anon().get(f"/post//{post['id']}")

	assert_status(r, 308)
	assert r.location == f"/post/{post['id']}"


@pytest.mark.parametrize("route", [r for r in ROUTES if r.access != PUBLIC], ids=_id)
def test_a_browser_without_a_session_is_given_one(route):
	client = anon()

	client.request(route.method, _path(route))

	assert session.cookie_name() in client.cookies


# The two whose purpose is to write the browser's own session (pages/test_mobile_tip, the 18+ confirmation)
_WRITE_THE_SESSION = {("POST", "/allow_nsfw"), ("POST", "/dismiss_mobile_tip")}


@pytest.mark.parametrize("route", [r for r in ROUTES if r.access == PUBLIC and (r.method, r.path) not in _WRITE_THE_SESSION], ids=_id)
def test_public_routes_give_no_session(route):
	client = anon()

	client.request(route.method, _path(route))

	assert session.cookie_name() not in client.cookies


# Spellings of the System account's id (1) and of others an id can't be written as
_NOT_IDS = {
	"leading zero": "01",
	"fullwidth digits": chr(0xFF11),
	"plus sign": "+1",
	"leading space": "%201",
	"underscore": "1_0",
	"zero": "0",
	"too large": str(2**31),
}


@pytest.mark.parametrize("spelling", _NOT_IDS)
@pytest.mark.parametrize("route", [r for r in ROUTES if "<id>" in r.path], ids=_id)
def test_an_id_written_otherwise_is_404(route, spelling):
	path = _path(route).replace(_UNUSED_ID, _NOT_IDS[spelling])

	assert_status(anon().request(route.method, path), 404)
