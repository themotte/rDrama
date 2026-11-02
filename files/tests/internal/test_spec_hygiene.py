'''
Keeps the spec tier usable as a clean-room specification: spec code outside the harness may reach the application only through the harness's public API, may not use in-process tricks that wouldn't work against a separately running implementation, and must not depend on particular row ids.
'''
import ast
import re
from pathlib import Path

import pytest

SPEC_DIR = Path(__file__).resolve().parent.parent / "spec"
HARNESS_DIR = SPEC_DIR / "harness"
HARNESS_PACKAGE = "files.tests.spec.harness"
FORBIDDEN_HARNESS_MODULES = {f"{HARNESS_PACKAGE}.backend"}
# Tools that only work by reaching into the process under test
FORBIDDEN_TOP_LEVEL_MODULES = {"flask", "werkzeug", "freezegun", "time_machine", "requests", "responses", "unittest", "itsdangerous"}
FORBIDDEN_MODULE_PREFIXES = ("sqlalchemy.orm",)
HARDCODED_ID_PATH = re.compile(r"/\d+(?:[/?#]|$)")

SPEC_FILES = sorted(p for p in SPEC_DIR.glob("**/*.py") if HARNESS_DIR not in p.parents)
SPEC_TEST_FILES = [p for p in SPEC_FILES if p.name.startswith("test_")]


def _imported_modules(tree):
	for node in ast.walk(tree):
		if isinstance(node, ast.Import):
			yield from (alias.name for alias in node.names)
		elif isinstance(node, ast.ImportFrom):
			module = node.module or ""
			yield module
			# `from package import submodule` reaches the submodule too
			yield from (f"{module}.{alias.name}" for alias in node.names)


def _is_forbidden(module):
	top = module.split(".")[0]
	if top == "files":
		in_harness = module == HARNESS_PACKAGE or module.startswith(HARNESS_PACKAGE + ".")
		return not in_harness or any(module == m or module.startswith(m + ".") for m in FORBIDDEN_HARNESS_MODULES)
	return top in FORBIDDEN_TOP_LEVEL_MODULES or module.startswith(FORBIDDEN_MODULE_PREFIXES)


@pytest.mark.parametrize("path", SPEC_FILES, ids=lambda p: str(p.relative_to(SPEC_DIR)))
def test_spec_code_imports_only_the_harness(path):
	tree = ast.parse(path.read_text())
	offending = sorted({m for m in _imported_modules(tree) if _is_forbidden(m)})
	assert not offending, f"{path.name} reaches past the harness: {offending}"


@pytest.mark.parametrize("path", SPEC_TEST_FILES, ids=lambda p: str(p.relative_to(SPEC_DIR)))
def test_spec_tests_do_not_hardcode_row_ids_in_urls(path):
	tree = ast.parse(path.read_text())
	offending = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str) and HARDCODED_ID_PATH.search(node.value)]
	assert not offending, f"{path.name} hardcodes ids in URLs (take them from created rows instead): {offending}"


def test_there_are_spec_tests_to_check():
	assert SPEC_TEST_FILES


@pytest.mark.parametrize("module, forbidden", [
	("files.tests.spec.harness", False),
	("files.tests.spec.harness.db", False),
	("files.tests.spec.harness.backend", True),
	("files.classes.user", True),
	("flask", True),
	("sqlalchemy.orm.session", True),
	("sqlalchemy", False),
	("json", False),
])
def test_forbidden_module_rules(module, forbidden):
	assert _is_forbidden(module) == forbidden
