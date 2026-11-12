'''
What the site's pages offer: for each page a spec test views, by viewer kind, the requests its links, forms and scripts lead to. A run of the whole spec tier fails when a page leads somewhere no route answers, or runs a script call nobody has classified; with RDRAMA_AFFORDANCES_OUT set it also writes the map there, for the contract writeup (../rDrama-contract, pages.md).

Scripts are read through CALLS and SCRIPTS below, which know the site's own scripts; internal/test_affordance_tables.py keeps them equal to the scripts and templates.
'''
import json
import re
from typing import Callable, NamedTuple
from urllib.parse import parse_qsl, unquote, urlsplit

from files.tests import testenv
from files.tests.spec.harness.pages import STORED_TEXT_COLUMNS, form_method, leads, site_address
from files.tests.spec.harness.routes import ROUTES, match, off_spec

SPEC = testenv.REPO_ROOT / "files" / "tests" / "spec"
JS = testenv.REPO_ROOT / "files" / "assets" / "js"
TEMPLATES = testenv.REPO_ROOT / "files" / "templates"
VIEWER_ANON = "anon"
PLACEHOLDER = "1"


class Affordance(NamedTuple):
	kind: str  # link, copy, form, script, background, embed
	method: str
	address: str  # an address on the site, or with `route`, a path of the route table; either with its query
	fields: tuple[str, ...] = ()
	route: bool = False


# A JavaScript call's argument: its source, its value when it is literal text (non-literal parts read as PLACEHOLDER), and its value as JSON when it is an object or array (None otherwise)
class Arg(NamedTuple):
	source: str
	text: str
	data: object


class Call(NamedTuple):
	'''A script function the page's attributes call: `sources` are the (script, address literal) of the requests it makes, as written in the script; `requests` gives them for the call's arguments and the element the attribute is on.'''
	sources: tuple[tuple[str, str], ...]
	requests: Callable[[list[Arg], object], list[Affordance]]


def _route(method, path, kind="script"):
	'''A call that always makes the request of one route.'''
	return lambda a, e: [Affordance(kind, method, path, route=True)]


def _toast(default_method=None):
	def requests(a, element):
		method = a[2].text if len(a) > 2 else default_method
		assert method, "a request with no method"
		return [Affordance("script", method.upper(), a[1].text)]
	return Call((), requests)


def _form_post(a, form):
	# The template scan reads attributes without their element
	if form is None: return []
	return [Affordance("script", "POST", form.get("action"), _field_names(form))]


def _notes(a, element):
	user = a[0].data if isinstance(a[0].data, dict) else {"url": f"/@{PLACEHOLDER}", "notes": [{"id": PLACEHOLDER}]}
	return [Affordance("script", "POST", f"{user['url']}/create_note")] + [Affordance("script", "POST", f"{user['url']}/delete_note/{note['id']}") for note in user["notes"]]


def _popover(a, element):
	author = a[0].data if isinstance(a[0].data, dict) else {"url": f"/@{PLACEHOLDER}"}
	return [Affordance("link", "GET", author["url"])]


_FILTER = (("filter_actions.js", "/admin/update_filter_status"),)

CALLS = {
	"postToast": _toast(),
	"postToastReload": _toast(),
	"postToastSimple": _toast("POST"),
	"postToastSwitch": _toast(),
	"submitFormAjax": Call((), _form_post),
	"fillnote": Call((("comments+submission_listing.js", "/create_note"), ("comments+submission_listing.js", "/delete_note/")), _notes),
	"popclick": Call((), _popover),
	"vote": Call((("comments+submission_listing.js", "/vote/"),), lambda a, e: [Affordance("script", "POST", f"/vote/{a[0].text.removesuffix('-mobile')}/<id>/<text>", route=True)]),
	"moderate": Call(_FILTER, _route("POST", "/admin/update_filter_status")),
	"filter_new_status": Call(_FILTER, _route("POST", "/admin/update_filter_status")),
	"filter_new_comment_status": Call(_FILTER, _route("POST", "/admin/update_filter_status")),
	"report_postModal": Call((("report_post_modal.js", "/report/post/"),), _route("POST", "/report/post/<id>")),
	"report_commentModal": Call((("comments_v.js", "/report/comment/"),), _route("POST", "/report/comment/<id>")),
	"delete_postModal": Call((("delete_post_modal.js", "/delete_post/"),), _route("POST", "/delete_post/<id>")),
	"delete_commentModal": Call((("comments_v.js", "/delete/comment/"),), _route("POST", "/delete/comment/<id>")),
	"banModal": Call((("ban_modal.js", "/ban_user/"),), _route("POST", "/ban_user/<id>?form")),
	"showShadowbanModal": Call((("userpage_v.js", "/shadowban/"),), _route("POST", "/shadowban/<id>")),
	"post_comment": Call((("comments_v.js", "/comment"),), _route("POST", "/comment")),
	"post_reply": Call((("comments_v.js", "/reply"),), _route("POST", "/reply")),
	"comment_edit": Call((("comments_v.js", "/edit_comment/"),), _route("POST", "/edit_comment/<id>")),
	"block_user": Call((("settings_blocks.js", "/settings/block"),), _route("POST", "/settings/block")),
	"removeFollower": Call((("followers.js", "/remove_follow/"),), _route("POST", "/remove_follow/<text>")),
	"removeFollowing": Call((("following.js", "/unfollow/"),), _route("POST", "/unfollow/<text>")),
	"morecomments": Call((("comments.html", "/morecomments/"),), _route("GET", "/morecomments/<id>")),
	"viewmore": Call((("submission.html", "/viewmore/"),), _route("GET", "/viewmore/<id>/<text>/<text>?ids")),
	"autoSuggestTitle": Call((("submit.js", "/submit/title"),), _route("GET", "/submit/title?url", "background")),
	"checkRepost": Call((("submit.js", "/is_repost"),), _route("POST", "/is_repost", "background")),
}
'''The site's script functions that make requests, by name.'''

LOCAL = {
	"changename", "charLimit", "checkForRequired", "collapse_comment", "draft", "emailVerifyText", "expandDesktopImage", "expandMarkdown", "expandText", "hide_image",
	"makeBold", "makeItalics", "makeLink", "makeQuote", "markdown", "onFormSubmit", "openReplyBox", "pinned_timestamp", "savetext", "send_note", "sort_table", "timestamp",
	"toggleEdit", "toggleElement", "togglePostEdit", "togglevideo",
}
'''The site's script functions that make no request of their own (send_note's is fillnote's).'''

BUILTIN = {"document.getElementById", "form.submit", "location.reload", "false"}
'''What handlers call or say of the browser's own that makes no request (a form a script submits is listed as the form; "return false" keeps a form from being sent).'''

DOM_MEMBERS = {"classList", "add", "remove", "toggle", "disabled", "submit", "value", "checked"}
'''What may follow a call of the browser's own in a handler, as in document.getElementById('x').classList.add('y').'''

SCRIPTS = {
	("signup.js", "/is_available/"): [Affordance("background", "GET", "/is_available/<text>", route=True)],
	("settings_profile.js", "/settings/profile"): [Affordance("script", "POST", "/settings/profile?background", route=True)],
	("home.html", "/dismiss_mobile_tip"): [Affordance("script", "POST", "/dismiss_mobile_tip", route=True)],
}
'''Requests scripts make that no attribute calls for, by the script (or the template whose inline script it is, by its path under the templates) and the address literal written there: credited to pages that load the script, or hold the literal in an inline script.'''

PASS_THROUGH = {"header.js": 4, "userpage_v.js": 1, "settings_profile.js": 1}
'''How many of each script's requests take their address from their caller (postToast and its kin, submitFormAjax, the profile settings' helper).'''

VENDORED = {"bootstrap.js", "chat_done.js", "lozad.js", "micromodal.js"}
# Templates outside the spec: the chat, and the admins' request-performance controls
UNSPECIFIED_TEMPLATES = ("chat/", "admin/performance/")


# Parsing script attributes

_TOKEN = re.compile(r"""\s*(?:(?P<str>'(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*"|`(?:\\.|[^`\\])*`)|(?P<num>\d+(?:\.\d+)?)|(?P<name>[A-Za-z_$][\w$]*(?:\s*\.\s*[A-Za-z_$][\w$]*)*)|(?P<op>==?=?|!==?|&&|\|\||[(){}\[\],;+?:!<>*/.-]))""")


def _tokens(source: str) -> list[tuple[str, str, int, int]]:
	tokens, pos = [], 0
	while source[pos:].strip():
		m = _TOKEN.match(source, pos)
		if not m: raise ValueError(f"can't read {source[pos:pos + 30]!r}")
		kind = m.lastgroup
		tokens.append((kind, m[kind], m.start(kind), m.end()))
		pos = m.end()
	return tokens


def _split(tokens, separator):
	'''Tokens split at `separator` outside brackets.'''
	parts, depth, current = [], 0, []
	for token in tokens:
		if token[0] == "op" and token[1] in ("(", "[", "{"): depth += 1
		if token[0] == "op" and token[1] in (")", "]", "}"): depth -= 1
		if depth == 0 and token[0] == "op" and token[1] == separator:
			parts.append(current)
			current = []
		else:
			current.append(token)
	parts.append(current)
	return [p for p in parts if p]


def _closing(tokens) -> int:
	'''The index of the bracket closing the one tokens[0] opens.'''
	depth = 0
	for i, token in enumerate(tokens):
		if token[0] == "op" and token[1] in ("(", "[", "{"): depth += 1
		if token[0] == "op" and token[1] in (")", "]", "}"): depth -= 1
		if depth == 0: return i
	raise ValueError("an unclosed bracket")


def _string(token: str) -> str:
	body = token[1:-1]
	if token[0] == "`": body = re.sub(r"\$\{[^}]*\}", PLACEHOLDER, body)
	return re.sub(r"\\(.)", r"\1", body)


def _arg(tokens, source) -> Arg:
	text = source[tokens[0][2]:tokens[-1][3]].strip()
	data = None
	if tokens[0][1] in ("{", "["):
		try:
			data = json.loads(text)
		except ValueError:
			data = None  # an object written in script, not JSON: read as non-literal
	pieces = []
	for part in _split(tokens, "+"):
		if len(part) == 1 and part[0][0] == "str": pieces.append(_string(part[0][1]))
		elif len(part) == 1 and part[0][0] == "num": pieces.append(part[0][1])
		else: pieces.append(PLACEHOLDER)
	return Arg(text, "".join(pieces), data)


def _statement(tokens, source) -> list[tuple[str, list[Arg]]]:
	if tokens and tokens[0][1] == "return": tokens = tokens[1:]
	if not tokens: return []
	kind, name = tokens[0][0], re.sub(r"\s", "", tokens[0][1])
	if kind != "name": raise ValueError(f"not a call: {source!r}")
	rest = tokens[1:]
	if not rest:
		return [(name, [])]
	if rest[0][1] == "=" and len(rest) > 1:
		return [(name, [_arg(rest[1:], source)])]
	if rest[0][1] != "(":
		raise ValueError(f"not a call: {source!r}")
	end = _closing(rest)
	calls = [(name, [_arg(part, source) for part in _split(rest[1:end], ",")])]
	rest = rest[end + 1:]
	# What follows a call: only a chain of the browser's own members, perhaps assigned to
	while rest:
		if rest[0][1] == "." and len(rest) > 1 and rest[1][0] == "name" and set(re.sub(r"\s", "", rest[1][1]).split(".")) <= DOM_MEMBERS:
			rest = rest[2:]
		elif rest[0][1] == "(":
			end = _closing(rest)
			rest = rest[end + 1:]
		elif rest[0][1] == "=" and len(rest) > 1:
			value = rest[1:]
			calls += _statement(value, source) if len(value) > 1 and value[0][0] == "name" and value[1][1] == "(" else [("", [_arg(value, source)])]
			rest = []
		else:
			raise ValueError(f"can't read what follows {name}() in {source!r}")
	return calls


def parse_calls(source: str) -> list[tuple[str, list[Arg]]]:
	'''The statements of an event-handler attribute, as (callee, its arguments): for an assignment, the name assigned to and the value; a value assigned that is no call has the callee "".'''
	return [call for statement in _split(_tokens(source), ";") for call in _statement(statement, source)]


def script_requests(source: str, element) -> tuple[list[Affordance], list[str]]:
	'''The requests an event-handler attribute makes, and the calls in it nobody has classified.'''
	found, unknown = [], []
	try:
		calls = parse_calls(source)
	except ValueError:
		return [], [f"unreadable handler {source!r}"]
	for name, args in calls:
		if name in ("location.href", "window.location.href"):
			found.append(Affordance("script", "GET", args[0].text))
		elif name in CALLS:
			found += CALLS[name].requests(args, element)
		elif name not in LOCAL and name not in BUILTIN and name != "":
			unknown.append(name)
	return found, unknown


# Reading pages

def _field_names(form) -> tuple[str, ...]:
	controls = form.xpath(".//input | .//select | .//textarea | .//button")
	if form.get("id"):
		controls += form.getroottree().xpath("//*[@form=$f]", f=form.get("id"))
	# A name ending in a row id ("volunteer-assignment-<id>") is one field per row
	return tuple(sorted({re.sub(r"-\d+$", "-<id>", c.get("name")) for c in controls if c.get("name")}))


def _script_sent(form) -> bool:
	'''Whether a form's own handler keeps the browser from sending it (its script sends it instead, or nothing does).'''
	calls = parse_calls(form.get("onsubmit") or "")
	return any(name in ("false", "submitFormAjax") for name, _ in calls)


def page_affordances(html: str, page_url: str, host: str) -> tuple[list[Affordance], list[str]]:
	'''What a page offers, and the script calls in it nobody has classified.'''
	import lxml.html
	if not html.strip(): return [], []
	document = lxml.html.document_fromstring(html)
	# Links and embeds as the harness reads them (spec/harness/pages.py)
	found = [Affordance(kind, method, address) for kind, method, address in leads(document, page_url, host) if kind != "form"]
	unknown = []
	for value in document.xpath("//@data-clipboard-text"):
		# What a page offers to copy is an address only when written as one (it may be a token)
		if value.startswith(("/", "http:", "https:")) and (address := site_address(value, page_url, host)):
			found.append(Affordance("copy", "GET", address))
	# Forms, unless their own handler keeps the browser from sending them: the harness checks only those without a handler
	for form in document.xpath("//form"):
		method = form_method(form)
		if _script_sent(form) or not method: continue
		address = site_address(form.get("action") or "", page_url, host)
		if address: found.append(Affordance("form", method, address, _field_names(form)))
	for element in document.iter():
		if not isinstance(element.tag, str): continue
		for attribute, source in element.attrib.items():
			if attribute.startswith("on"):
				requests, unclassified = script_requests(source, element)
				found += [r if r.route else r._replace(address=site_address(r.address, page_url, host) or r.address) for r in requests]
				unknown += unclassified
	loaded = {urlsplit(src).path.rsplit("/", 1)[-1] for src in document.xpath("//script/@src")}
	inline = "".join(document.xpath("//script[not(@src)]/text()"))
	for (script, literal), requests in SCRIPTS.items():
		if script in loaded or (script.endswith(".html") and literal in inline):
			found += requests
	return found, unknown


# Recording during the spec run

_rows: set[tuple] = set()
_dead: set[str] = set()
_unclassified: set[str] = set()
_failures: set[str] = set()
_recording = False
_connected = False
_stored_text_columns: list[tuple[str, str]] | None = None
_app_routes: set[tuple[str, str]] | None = None


def _viewer(g) -> str:
	v = getattr(g, "v", None)
	if v is None: return VIEWER_ANON
	return f"admin {v.account_admin_level}" if v.account_admin_level else "member"


def _without_stored_text(html: str, db) -> str:
	'''The page without the rendered text users wrote (stored in the database and shown as it is), whose links are theirs, not the page's.'''
	global _stored_text_columns
	from sqlalchemy import text
	if _stored_text_columns is None:
		_stored_text_columns = [tuple(row) for row in db.execute(text(STORED_TEXT_COLUMNS))]
	# Only text holding a link or an image can add to what the page offers
	values = {value for table, column in _stored_text_columns for (value,) in db.execute(text(f'SELECT "{column}" FROM "{table}" WHERE "{column}" ILIKE \'%href=%\' OR "{column}" ILIKE \'%src=%\''))}
	for value in sorted(values, key=len, reverse=True):
		html = html.replace(value, "")
	return html


def target(a: Affordance) -> str | None:
	'''The route-table row ("METHOD path") that answers an affordance's request, or the address of what's served beside the spec; None if nothing does.'''
	path = a.address.partition("?")[0]
	if a.route:
		return f"{a.method} {path}" if any(r.method == a.method and r.path == path for r in ROUTES) else None
	if off_spec(path): return f"{a.method} {path.rstrip('/') or '/'}"
	found = match(a.method, a.address)
	return f"{found.route.method} {found.route.path}" if found else None


def _routers_target(app, host: str, a: Affordance) -> str | None:
	'''target() as the app's router answers it, which target() must agree with.'''
	from werkzeug.exceptions import HTTPException
	from werkzeug.routing import RequestRedirect
	from files.tests import route_table
	global _app_routes
	# As the server hands it to the router: decoded
	path = unquote(urlsplit(a.address).path)
	if a.route:
		if _app_routes is None: _app_routes = set(route_table.app_routes(app))
		return f"{a.method} {path}" if (a.method, path) in _app_routes else None
	# Answered by other services (the chat) or by rules the table leaves out
	if off_spec(path): return target(a)
	adapter = app.url_map.bind(host)
	for _ in range(2):
		try:
			rule, _args = adapter.match(path, a.method, return_rule=True)
			return f"{a.method} {route_table.path_of(rule.rule)}"
		except RequestRedirect as redirect:
			path = urlsplit(redirect.new_url).path
		except HTTPException:
			return None
	return None


def _record(sender, response, **extra):
	from flask import request
	if not _recording or request.url_rule is None: return
	try:
		_record_page(sender, response)
	except Exception as e:
		# Reported with the run's other findings, failing it; the page itself is answered as it would be
		_failures.add(f"{request.method} {request.path}: {e!r}")


def _record_page(sender, response):
	from flask import g, request
	from files.tests import route_table
	if request.method not in ("GET", "POST"): return
	if response.status_code != 200 or response.mimetype != "text/html" or "Authorization" in request.headers: return
	page = f"{request.method} {route_table.path_of(request.url_rule.rule)}"
	viewer = _viewer(g)
	html = _without_stored_text(response.get_data(as_text=True), g.db)
	found, unknown = page_affordances(html, request.url, request.host)
	_rows.add((page, viewer, "page", "", "", "", ""))
	_unclassified.update(f"{page}: {name}" for name in unknown)
	for a in found:
		row = target(a)
		if row != (routers := _routers_target(sender, request.host, a)):
			_failures.add(f"{page}: {a.kind} {a.method} {a.address} reaches {routers} by the router, {row} by the harness's match()")
		if row is None:
			# Dead links and embeds are the harness's to report
			if a.kind not in ("link", "embed"):
				_dead.add(f"{page}: {a.kind} {a.method} {a.address}")
			continue
		query = ",".join(sorted({key for key, _ in parse_qsl(urlsplit(a.address).query, keep_blank_values=True)}))
		method, path = row.split(" ", 1)
		_rows.add(("*", "*", a.kind, method, path, "", "") if a.kind == "embed" else (page, viewer, a.kind, method, path, query, ",".join(a.fields)))


def start(path):
	global _recording, _connected
	if not _connected:
		import flask
		from files.__main__ import app
		flask.request_finished.connect(_record, app)
		_connected = True
	_recording = path.is_relative_to(SPEC)


def stop():
	global _recording
	_recording = False


_KEYS = ("rows", "dead", "unclassified", "failures")


def output() -> dict:
	return {"rows": sorted(_rows), "dead": sorted(_dead), "unclassified": sorted(_unclassified), "failures": sorted(_failures)}


def merge(outputs: list[dict]) -> dict:
	return {key: sorted({tuple(x) if isinstance(x, list) else x for o in outputs for x in o[key]}) for key in _KEYS}


def problems(merged: dict) -> dict[str, list[str]]:
	'''What fails the run, by heading.'''
	return {heading: merged[key] for key, heading in (("dead", "page affordances no route answers (affordances.py: forms and what scripts request)"), ("unclassified", "script calls in pages nobody has classified (affordances.py)"), ("failures", "pages the affordance recorder failed on")) if merged[key]}


COLUMNS = ("page", "viewer", "kind", "method", "target", "query", "fields")


def table(rows) -> str:
	'''The map as tab-separated values, with a heading line.'''
	return "\n".join("\t".join(row) for row in [COLUMNS, *sorted(rows)]) + "\n"
