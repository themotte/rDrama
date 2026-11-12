'''The harness's route matching (spec/harness/routes.py match) answers as the app's router does, over paths built from the table's own segments.'''
import re
from urllib.parse import unquote, urlsplit

from werkzeug.exceptions import HTTPException
from werkzeug.routing import RequestRedirect

from files.__main__ import app
from files.tests import route_table
from files.tests.spec.harness import config
from files.tests.spec.harness.routes import NOT_IDS, ROUTES, match, off_spec

METHODS = ("GET", "POST", "PUT", "HEAD")


def _segments(path: str) -> list[str]:
	return path.strip("/").split("/") if path != "/" else []


def _value(segment: str) -> str:
	return re.sub(r"<([^>]+)>", lambda m: {"id": "5", "text": "x", "path": "x/y"}.get(m.group(1)) or m.group(1).split("|")[0], segment)


# Every fixed segment at each depth of the table, for filling variables with what other rows have there
_FIXED = {}
for _route in ROUTES:
	for _depth, _segment in enumerate(_segments(_route.path)):
		if "<" not in _segment:
			_FIXED.setdefault(_depth, set()).add(_segment)
_OTHERS = ["x", "5", "@x", "%41b", "a%2Fb", *NOT_IDS.values()]
# What's served beside the spec, which the router reaches by rules the table leaves out (the chat is another service's)
_OFF_SPEC = ["/performance", "/performance/", "/performance/x"]


def _paths():
	'''Each row's path with valid values, with a trailing "/", a "/" more at the start or end, and doubled and tripled "/" inside; then each variable in turn filled with every fixed segment found at its depth and with odd values.'''
	paths = set()
	for route in ROUTES:
		segments = _segments(route.path)
		base = "/" + "/".join(_value(s) for s in segments)
		paths |= {base, base.rstrip("/") + "/", "/" + base, base + "//"}
		# Doubled and tripled "/" inside the path
		for i in [m.start() for m in re.finditer("/", base)][1:]:
			paths |= {base[:i] + "/" + base[i:], base[:i] + "//" + base[i:]}
		for depth, segment in enumerate(segments):
			if "<" not in segment:
				continue
			for fill in sorted(_FIXED.get(depth, set())) + _OTHERS:
				paths.add("/" + "/".join(fill if i == depth else _value(s) for i, s in enumerate(segments)))
	return sorted(paths | set(_OFF_SPEC))


def _routers_answer(method: str, path: str):
	'''What the app's router does with a request: ("row", "METHOD path"), ("redirect", the row it redirects to), ("off spec",) or None.'''
	adapter = app.url_map.bind(config.site_host())
	def row(target):
		rule, _ = adapter.match(target, method, return_rule=True)
		if rule.rule.startswith(route_table._UNSPECIFIED_PREFIXES):
			return None
		return f"{'GET' if method == 'HEAD' else method} {route_table.path_of(rule.rule)}"
	decoded = unquote(path)
	try:
		answer = row(decoded)
		return ("row", answer) if answer else ("off spec",)
	except RequestRedirect as redirect:
		try:
			return ("redirect", row(urlsplit(redirect.new_url).path))
		except HTTPException:
			return ("redirect", "an id out of range")
	except HTTPException:
		return None


def _harness_answer(method: str, path: str):
	found = match(method, path)
	if found is None:
		return ("off spec",) if off_spec(unquote(path)) else None
	return ("redirect" if found.redirected else "row", f"{found.route.method} {found.route.path}")


def test_the_harness_matches_paths_as_the_router_does():
	disagreements = []
	cases = 0
	for path in _paths():
		for method in METHODS:
			cases += 1
			router, harness = _routers_answer(method, path), _harness_answer(method, path)
			# After merging, the router redirects before reading ids; the harness names the row the merged path has
			if router == ("redirect", "an id out of range") and harness and harness[0] == "redirect":
				continue
			# What's beside the spec isn't the spec's to judge: the harness leaves the whole of it alone, served or not
			if harness == ("off spec",) and router in (None, ("off spec",)):
				continue
			if router != harness:
				disagreements.append(f"{method} {path}: router {router}, harness {harness}")
	assert cases > 10000
	assert disagreements == [], f"{len(disagreements)} of {cases} disagree:\n" + "\n".join(disagreements[:40])


def test_options_and_unlisted_paths_name_no_row():
	assert match("OPTIONS", "/") is None
	assert match("GET", "/no/such/page") is None
