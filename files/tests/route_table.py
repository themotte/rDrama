'''
The application's routes in the notation of the spec's route table (files/tests/spec/harness/routes.py), for the checks that keep the two equal. Reads the application, so it stays outside the spec tier.
'''
import ast
import inspect
import re
import textwrap

from files.tests.spec.harness import routes as table

# Outside the spec, like the chat service and the developer routes (which the test configuration doesn't register)
_UNSPECIFIED_PREFIXES = ("/performance/",)


def path_of(rule: str) -> str:
	'''A Werkzeug rule written in the table's notation.'''
	def variable(m):
		converter, args = m.group(1), m.group(2)
		if converter is None or converter in ("default", "string"): return "<text>"
		if converter == "any": return "<" + "|".join(word.strip().strip("'\"") for word in args.split(",")) + ">"
		return f"<{converter}>"
	path = re.sub(r"<(?:(\w+)(?:\((.*?)\))?:)?\w+>", variable, rule)
	return path.rstrip("/") or "/"


def app_routes(app) -> dict[tuple[str, str], object]:
	'''(method, path) of each specified route, mapped to its view function.'''
	routes = {}
	for rule in app.url_map.iter_rules():
		if rule.rule.startswith(_UNSPECIFIED_PREFIXES): continue
		for method in rule.methods - {"HEAD", "OPTIONS"}:
			key = (method, path_of(rule.rule))
			if key in routes: raise ValueError(f"two rules answer {key} (a trailing slash is optional on every path)")
			routes[key] = app.view_functions[rule.endpoint]
	return routes


def gates_of(view) -> tuple[str, bool]:
	'''The access its decorators give a view, and whether it takes API clients (refused by the admin decorator, or by a direct call in the view).'''
	from files.helpers import wrappers
	codes = {
		wrappers.auth_desired(lambda: 0).__code__: table.ANYONE,
		wrappers.auth_required(lambda: 0).__code__: table.USER,
		wrappers.is_not_permabanned(lambda: 0).__code__: table.USER_NOT_PERMABANNED,
	}
	admin_code = wrappers.admin_level_required(0)(lambda: 0).__code__
	access, layer = table.PUBLIC, view
	while True:
		if layer.__code__ is admin_code:
			access = table.admin(inspect.getclosurevars(layer).nonlocals["x"])
		elif layer.__code__ in codes:
			access = codes[layer.__code__]
		if not hasattr(layer, "__wrapped__"): break
		layer = layer.__wrapped__
	view_source = ast.parse(textwrap.dedent(inspect.getsource(layer)))
	refuses = any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "refuse_api_client" for node in ast.walk(view_source))
	return access, not (table.admin_level(access) is not None or refuses)
