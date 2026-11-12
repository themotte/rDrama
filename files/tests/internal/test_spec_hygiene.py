'''
Keeps the spec tier usable as a clean-room specification: spec code outside the harness may reach the application only through the harness's public API, may not use in-process tricks that wouldn't work against a separately running implementation, and must not depend on particular row ids or on markup beyond what pages share with the spec (harness/markup.py).
'''
import ast
import io
import re
import tokenize
from pathlib import Path

import pytest

from files.tests.internal import spec_export
from files.tests.testenv import REPO_ROOT

SPEC_DIR = Path(__file__).resolve().parent.parent / "spec"
HARNESS_DIR = SPEC_DIR / "harness"
HARNESS_PACKAGE = "files.tests.spec.harness"
# How the harness reaches an implementation, which tests go through the harness for
# The backends, the state reset, the page parser, and what the runner checks of a whole run, which tests mustn't reach into
FORBIDDEN_HARNESS_PREFIXES = (f"{HARNESS_PACKAGE}.backend", f"{HARNESS_PACKAGE}.process_", f"{HARNESS_PACKAGE}.run_record", f"{HARNESS_PACKAGE}.coverage", f"{HARNESS_PACKAGE}.pages", f"{HARNESS_PACKAGE}.html5", f"{HARNESS_PACKAGE}.state", f"{HARNESS_PACKAGE}.lifecycle")
# Tools that only work by reaching into the process under test, and page parsers (pages are read through harness/markup.py)
FORBIDDEN_TOP_LEVEL_MODULES = {"flask", "werkzeug", "freezegun", "time_machine", "requests", "responses", "unittest", "itsdangerous", "lxml", "bs4", "html5lib", "selectolax"}
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
	# The spec's own fixture runs each test in the lifecycle
	allowed = {f"{HARNESS_PACKAGE}.lifecycle"} if path == SPEC_DIR / "conftest.py" else set()
	offending = sorted({m for m in _imported_modules(tree) if _is_forbidden(m)} - allowed)
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
	("files.tests.spec.harness.html5", True),
	("files.tests.spec.harness.state", True),
	("files.tests.spec.harness.lifecycle", True),
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


# What the handed-over spec may name outside itself, and why
REFERENCES_ALLOWED = {
	"files.commands.volunteer_janitor_recalc": "the import path a built-in job stores (tasks_repeatable_python), which is data",
	"files.commands.leaderboard_recalc": "the import path a built-in job stores (tasks_repeatable_python), which is data",
	"files.tests.spec.harness.backend_inprocess": "the current implementation's own backend, which backend.py picks only when asked to",
}
REFERENCE = re.compile(r"\bfiles(?:[/.][\w-]+)+/?|\b[\w+-]+\.(?:py|html|js|css|md|sql|json)\b")
TEXT_TOKENS = {tokenize.STRING, tokenize.COMMENT, tokenize.FSTRING_MIDDLE}


def _texts(path: Path) -> list[tuple[int, str]]:
	'''A file's comments and strings (all of it, for a file that isn't Python), with their lines.'''
	if path.suffix != ".py":
		return list(enumerate(path.read_text().splitlines(), 1))
	return [(token.start[0], token.string) for token in tokenize.generate_tokens(io.StringIO(path.read_text()).readline) if token.type in TEXT_TOKENS]


def _outside(reference: str, exported: set[str], exported_names: set[str], repository_names: set[str]) -> bool:
	if reference.startswith("files"):
		path = reference.rstrip("/") if "/" in reference else reference.replace(".", "/")
		return not (path in exported or f"{path}.py" in exported or any(name.startswith(path + "/") for name in exported))
	return reference in repository_names and reference not in exported_names


def test_the_handed_over_spec_names_nothing_outside_it():
	files = spec_export.exported()
	exported = {str(f.relative_to(REPO_ROOT)) for f in files}
	exported_names = {Path(name).name for name in exported}
	repository_names = {f.name for f in spec_export.repository_files()}
	found = []
	for path in files:
		for line, text in _texts(path):
			found += [f"{path.relative_to(REPO_ROOT)}:{line}: {reference}" for reference in REFERENCE.findall(text) if reference not in REFERENCES_ALLOWED and _outside(reference, exported, exported_names, repository_names)]
	assert found == [], "the spec names what isn't handed over with it:\n" + "\n".join(found)


def test_the_handover_leaves_out_the_in_process_backend():
	assert {f.name for f in spec_export.exported()} >= {"backend.py", "backend_process.py"} and "backend_inprocess.py" not in {f.name for f in spec_export.exported()}


def _is_exported_module(module: str, exported: set[str]) -> bool:
	path = module.replace(".", "/")
	return f"{path}.py" in exported or f"{path}/__init__.py" in exported


def test_the_handed_over_spec_imports_nothing_outside_it():
	files = spec_export.exported()
	exported = {str(f.relative_to(REPO_ROOT)) for f in files}
	repository = {str(f.relative_to(REPO_ROOT)) for f in spec_export.repository_files()}
	found = []
	for path in files:
		if path.suffix != ".py":
			continue
		for node in ast.walk(ast.parse(path.read_text())):
			if isinstance(node, ast.Import):
				modules = [alias.name for alias in node.names]
			elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
				# `from package import name` reaches the module of that name, where there is one
				modules = [node.module] + [f"{node.module}.{alias.name}" for alias in node.names if _is_exported_module(f"{node.module}.{alias.name}", repository)]
			else:
				continue
			found += [f"{path.relative_to(REPO_ROOT)}:{node.lineno}: {module}" for module in modules if module.split(".")[0] == "files" and module not in REFERENCES_ALLOWED and not _is_exported_module(module, exported)]
	assert found == [], "the spec imports what isn't handed over with it:\n" + "\n".join(found)
