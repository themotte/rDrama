'''
The tables affordances.py reads scripts with stay equal to the site's templates and scripts, including templates no spec test renders.
'''
import re

import pytest

from files.tests import affordances
from files.tests.affordances import BUILTIN, CALLS, JS, LOCAL, PASS_THROUGH, SCRIPTS, TEMPLATES, UNSPECIFIED_TEMPLATES, VENDORED

ATTRIBUTE_START = r"(?<![\w.$-])on[a-z]+="
HANDLER = re.compile(ATTRIBUTE_START + r"""("([^"]*)"|'([^']*)')""")
# Where a script makes a request, or leaves the page
REQUEST_SITE = re.compile(r"""\.open\(|\bfetch\(|\bsendBeacon\(|\bpostToast\w*\(|\bpost\(|\blocation(?:\.href)?\s*=(?!=)|\.submit\(\)""")
DEFINITION = r"function {0}\b|(?<![\w.]){0}\s*=[^=]"


def _templates():
	'''The site's templates by path, without their comments.'''
	templates = {}
	for path in sorted(TEMPLATES.rglob("*.html")):
		name = path.relative_to(TEMPLATES).as_posix()
		if not name.startswith(UNSPECIFIED_TEMPLATES):
			templates[name] = re.sub(r"\{#.*?#\}", "", path.read_text(), flags=re.S)
	return templates


def _scripts():
	'''The site's own scripts: its script files by name, and its templates' inline scripts by template path.'''
	scripts = {path.name: path.read_text() for path in sorted(JS.rglob("*.js")) if path.name not in VENDORED and "vendor" not in path.relative_to(JS).parts}
	for name, text in _templates().items():
		inline = "\n".join(re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", text, re.S))
		if inline: scripts[name] = inline
	return scripts


def _static(source: str) -> str:
	'''A template's attribute with its template code read as placeholder values, each branch of a condition its own statement.'''
	return re.sub(r"\{%.*?%\}", ";", re.sub(r"\{\{.*?\}\}", affordances.PLACEHOLDER, source))


def _handlers():
	found = []
	for name, text in _templates().items():
		matches = list(HANDLER.finditer(text))
		assert len(matches) == len(re.findall(ATTRIBUTE_START, text)), f"{name} has an event-handler attribute this scan can't read"
		found += [(name, _static(m[2] if m[2] is not None else m[3])) for m in matches]
	return found


def test_every_handler_attribute_calls_classified_functions():
	unknown = [f"{name}: {u}" for name, source in _handlers() for u in affordances.script_requests(source, None)[1]]
	assert unknown == []


def test_the_classified_functions_are_the_sites():
	text = "\n".join(_scripts().values())
	assert [name for name in sorted(CALLS.keys() | LOCAL) if not re.search(DEFINITION.format(re.escape(name)), text)] == []


def test_the_classified_functions_are_called():
	called = {callee for _, source in _handlers() for callee, _ in affordances.parse_calls(source)}
	assert sorted((CALLS.keys() | LOCAL | BUILTIN) - called) == []


def _request_sites():
	'''(script, the address literal its request is written with), and how many requests each script makes with an address from its caller.'''
	literal, passed = set(), {}
	for name, text in _scripts().items():
		for line in text.splitlines():
			if not REQUEST_SITE.search(line) or re.match(r"\s*function\s", line): continue
			m = re.search(r"""['"`](/[^'"`$]*)""", line)
			if m: literal.add((name, re.split(r"\{%|\?", m[1])[0]))
			else: passed[name] = passed.get(name, 0) + 1
	return literal, passed


def test_every_request_a_script_makes_is_claimed():
	literal, passed = _request_sites()
	claimed = {source for call in CALLS.values() for source in call.sources} | SCRIPTS.keys()
	assert sorted(literal - claimed) == [], "requests no entry of CALLS or SCRIPTS claims"
	assert sorted(claimed - literal) == [], "entries claiming requests no script makes"
	assert passed == PASS_THROUGH


@pytest.fixture(scope="module")
def app():
	from files.__main__ import app
	return app


def test_the_classified_requests_reach_routes():
	wrong = []
	for name, source in _handlers():
		for callee, args in affordances.parse_calls(source):
			if callee not in CALLS: continue
			for request in CALLS[callee].requests(args, None):
				if affordances.target(request) is None or (CALLS[callee].sources and not any(literal in request.address for _, literal in CALLS[callee].sources)):
					wrong.append(f"{name}: {callee} → {request.method} {request.address}")
	for (script, literal), requests in SCRIPTS.items():
		wrong += [f"{script}: {r.method} {r.address}" for r in requests if affordances.target(r) is None or literal not in r.address]
	assert wrong == []
