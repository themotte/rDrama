'''
Keeps the spec tier usable as a clean-room specification: spec code outside the harness may reach the application only through the harness's public API, may not use in-process tricks that wouldn't work against a separately running implementation, and must not depend on particular row ids or on markup beyond what pages share with the spec (harness/markup.py).
'''
import ast
import re
from pathlib import Path

import pytest

SPEC_DIR = Path(__file__).resolve().parent.parent / "spec"
HARNESS_DIR = SPEC_DIR / "harness"
HARNESS_PACKAGE = "files.tests.spec.harness"
# How the harness reaches an implementation, which tests go through the harness for
# The backends, and what the runner checks of a whole run, which tests mustn't reach into
FORBIDDEN_HARNESS_PREFIXES = (f"{HARNESS_PACKAGE}.backend", f"{HARNESS_PACKAGE}.process_", f"{HARNESS_PACKAGE}.run_record", f"{HARNESS_PACKAGE}.coverage", f"{HARNESS_PACKAGE}.pages")
# Tools that only work by reaching into the process under test, and page parsers (pages are read through harness/markup.py)
FORBIDDEN_TOP_LEVEL_MODULES = {"flask", "werkzeug", "freezegun", "time_machine", "requests", "responses", "unittest", "itsdangerous", "lxml", "bs4", "html5lib"}
FORBIDDEN_MODULE_PREFIXES = ("sqlalchemy.orm", "html.parser")
HARDCODED_ID_PATH = re.compile(r"/\d+(?:[/?#]|$)")
# XML namespace names carry years in their paths
W3C_NAMESPACE = re.compile(r"\{?http://www\.w3\.org/")

# Attributes in string constants: tests read pages through harness/markup.py instead
MARKUP_ATTRIBUTE = re.compile(r"""\b(?:id|class|for|href|src|name|value|action|title|content)=["']|\bdata-[a-z-]+=""")
MARKUP_TAG = re.compile(r"</?[a-z][a-z0-9]*[\s>/]")
# Methods that search text: re's, a compiled pattern's and a string's
SEARCHES = {"findall", "finditer", "search", "match", "fullmatch", "sub", "subn", "split", "index", "find", "rfind", "rindex", "count", "partition", "startswith"}
MARKUP_ALLOWED = {
	# What written text renders to is the rendering spec's subject
	"rendering",
	# Serves other sites' pages
	"posts/test_fetchers.py",
	# Checks every address of a site file a page or stylesheet writes, wherever it writes it
	"pages/test_assets.py",
}

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
		return not in_harness or module.startswith(FORBIDDEN_HARNESS_PREFIXES)
	return top in FORBIDDEN_TOP_LEVEL_MODULES or module.startswith(FORBIDDEN_MODULE_PREFIXES)


@pytest.mark.parametrize("path", SPEC_FILES, ids=lambda p: str(p.relative_to(SPEC_DIR)))
def test_spec_code_imports_only_the_harness(path):
	tree = ast.parse(path.read_text())
	offending = sorted({m for m in _imported_modules(tree) if _is_forbidden(m)})
	assert not offending, f"{path.name} reaches past the harness: {offending}"


@pytest.mark.parametrize("path", SPEC_TEST_FILES, ids=lambda p: str(p.relative_to(SPEC_DIR)))
def test_spec_tests_do_not_hardcode_row_ids_in_urls(path):
	tree = ast.parse(path.read_text())
	offending = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str) and HARDCODED_ID_PATH.search(node.value) and not W3C_NAMESPACE.match(node.value)]
	assert not offending, f"{path.name} hardcodes ids in URLs (take them from created rows instead): {offending}"


def _reads_markup(path):
	relative = path.relative_to(SPEC_DIR)
	return not ({str(relative), relative.parts[0]} & MARKUP_ALLOWED)


def _not_page_reads(tree):
	'''Docstrings, the stored rendering a test compares with what it expects (a row's column, not a page), and other sites' pages the site is served.'''
	docstrings = {id(node.body[0].value) for node in ast.walk(tree) if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant)}
	renderings = {id(inner) for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "assert_same_html" and isinstance(node.args[0], ast.Subscript) for inner in ast.walk(node.args[1])}
	served = {id(inner) for node in ast.walk(tree) if isinstance(node, ast.Call) and ast.unparse(node.func) == "external_web.serve" for inner in ast.walk(node)}
	return docstrings | renderings | served


def _is_response_text(node):
	return isinstance(node, ast.Attribute) and node.attr in ("text", "body")


def _searches_response_text(node):
	'''`re.findall(..., r.text)`, `pattern.findall(r.text)`, `r.text.index(...)` and the like.'''
	if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in SEARCHES):
		return False
	return _is_response_text(node.func.value) or any(_is_response_text(arg) for arg in node.args)


def _markup_in(node):
	return isinstance(node, ast.Constant) and isinstance(node.value, str) and (MARKUP_ATTRIBUTE.search(node.value) or MARKUP_TAG.search(node.value))


@pytest.mark.parametrize("path", [p for p in SPEC_FILES if _reads_markup(p)], ids=lambda p: str(p.relative_to(SPEC_DIR)))
def test_spec_tests_read_pages_only_through_the_harness(path):
	tree = ast.parse(path.read_text())
	skipped = _not_page_reads(tree)
	attributes = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skipped and MARKUP_ATTRIBUTE.search(node.value)]
	# Searching a response for a tag, or with a pattern at all; sentinels are searched for with the asserts
	searched = [ast.unparse(node) for node in ast.walk(tree) if _searches_response_text(node) and (not isinstance(node.func.value, ast.Attribute) or not _is_response_text(node.func.value) or any(_markup_in(arg) for arg in ast.walk(node)))]
	assert (attributes, searched) == ([], []), f"{path.name} reads markup itself (use the helpers of harness/markup.py)"


def test_markup_exemptions_are_needed():
	exempt = [path for path in SPEC_FILES if not _reads_markup(path) and path.relative_to(SPEC_DIR).parts[0] != "rendering"]
	needless = [path.name for path in exempt if not any(_markup_in(node) or _searches_response_text(node) for node in ast.walk(ast.parse(path.read_text())))]
	assert exempt and needless == []


def test_there_are_spec_tests_to_check():
	assert SPEC_TEST_FILES


@pytest.mark.parametrize("module, forbidden", [
	("files.tests.spec.harness", False),
	("files.tests.spec.harness.db", False),
	("files.tests.spec.harness.backend", True),
	("files.tests.spec.harness.backend_inprocess", True),
	("files.tests.spec.harness.backend_process", True),
	("files.tests.spec.harness.process_proxy", True),
	("files.tests.spec.harness.run_record", True),
	("files.tests.spec.harness.coverage", True),
	("files.tests.spec.harness.pages", True),
	("files.classes.user", True),
	("flask", True),
	("sqlalchemy.orm.session", True),
	("sqlalchemy", False),
	("json", False),
])
def test_forbidden_module_rules(module, forbidden):
	assert _is_forbidden(module) == forbidden


def test_the_backends_provide_the_same_functions():
	from files.tests.spec.harness import backend_inprocess, backend_process
	assert backend_inprocess.__all__ == backend_process.__all__
	assert all(callable(getattr(module, name)) for module in (backend_inprocess, backend_process) for name in backend_process.__all__)
