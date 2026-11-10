'''
The variables the site reads are exactly those of the spec's environment table (spec/harness/config.py ENVIRONMENT), which a reimplementation must honor, and the current implementation's own below. bootstrap/site_env sets none outside the two.
'''
import ast
import os
import re

from files.tests.spec.harness.config import ENVIRONMENT, PRECONDITIONS
from files.tests.testenv import REPO_ROOT

# Read by the current implementation for itself; a reimplementation needn't
IMPLEMENTATION_ONLY = {
	"RDRAMA_SERVICE": "forces which part of the site the process runs, for the test runner",
	"RDRAMA_TESTING": "defers background work to the test harness and makes password hashes cheap",
	"DBG_LIMITER_DISABLED": "turns off the rate limits and the signup form's minimum filling time, for tests (rate limits are specified apart)",
	"ENFORCE_PRODUCTION": "refuses to start in Flask's debug mode unless false",
	"DBG_SQL_ANALYSIS": "a developer's per-request query report",
	"DBG_VOLUNTEER_PERMISSIVE": "a developer's switch relaxing volunteer duty's waits and filters",
}

# Read by the commands that start the current implementation rather than by its code
PROCESS = {
	"FLASK_APP": "names the application for the flask commands (set in the image)",
	"CORE_OVERRIDE": "the number of web worker processes (production sets it)",
	"WERKZEUG_DEBUG_PIN": "the development server's debugger PIN",
}
PROCESS_FILES = ["Dockerfile", "docker-compose.yml", "docker-compose-operation.yml", *(f"bootstrap/{p.name}" for p in (REPO_ROOT / "bootstrap").glob("supervisord.conf.*")), "bootstrap/init.sh"]

TRUE, FALSE = ("yes", "true", "t", "on", "1"), ("no", "false", "f", "off", "0")


def _python_files():
	yield from (p for p in (REPO_ROOT / "files").rglob("*.py") if "tests" not in p.relative_to(REPO_ROOT).parts)
	yield from (REPO_ROOT / "migrations").rglob("*.py")
	yield REPO_ROOT / "gunicorn_config.py"


def _is_environ(node):
	return (isinstance(node, ast.Name) and node.id == "environ") or (isinstance(node, ast.Attribute) and node.attr == "environ")


def _names_read():
	names = set()
	for path in _python_files():
		for node in ast.walk(ast.parse(path.read_text())):
			if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and (node.func.attr == "getenv" or (node.func.attr == "get" and _is_environ(node.func.value))):
				names.add(ast.literal_eval(node.args[0]))
			elif isinstance(node, ast.Subscript) and _is_environ(node.value):
				names.add(ast.literal_eval(node.slice))
	return names


def test_the_code_reads_the_table_and_its_own_variables():
	assert _names_read() == ENVIRONMENT.keys() | IMPLEMENTATION_ONLY.keys()


def test_every_process_variable_is_used_where_the_site_is_started():
	text = "\n".join((REPO_ROOT / f).read_text() for f in PROCESS_FILES)
	assert {name for name in PROCESS if not re.search(rf"\b{name}\b", text)} == set()


def test_site_env_sets_only_known_variables():
	lines = (REPO_ROOT / "bootstrap" / "site_env").read_text().splitlines()
	assert {line.split("=", 1)[0] for line in lines if line and not line.startswith("#")} - ENVIRONMENT.keys() - IMPLEMENTATION_ONLY.keys() == set()


def _value(name, default):
	raw = os.environ.get(name)
	if raw is None:
		return default
	if isinstance(default, bool):
		assert raw.strip().lower() in TRUE + FALSE, f"{name}={raw!r} isn't a boolean"
		return raw.strip().lower() in TRUE
	return raw.strip()


def test_the_spec_runs_with_its_preconditions():
	assert {name: _value(name, value) for name, value in PRECONDITIONS.items()} == PRECONDITIONS
