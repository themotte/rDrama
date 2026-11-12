'''
What spec/harness/backend_process.py says a runner provides holds for rDrama's: the environment of config.SPEC_RUN, Python RUNNER_PYTHON, and the packages of RUNNER_PACKAGES at their versions, which cover what the spec imports.
'''
import ast
import importlib.metadata
import os
import sys

from files.tests.spec.harness import config
from files.tests.spec.harness.backend_process import RUNNER_PACKAGES, RUNNER_PYTHON
from files.tests.testenv import REPO_ROOT

SPEC = REPO_ROOT / "files" / "tests" / "spec"


def test_the_spec_runs_at_the_values_of_spec_run():
	assert {name: os.environ.get(name) for name in config.SPEC_RUN} == config.SPEC_RUN


def test_every_variable_has_one_source():
	sources = [set(config.SPEC_RUN), set(config.RUNNER_CHOSEN), set(config.PRECONDITIONS), config.SET_BY_HARNESS]
	assert sorted(name for source in sources for name in source) == sorted(config.ENVIRONMENT)


def test_the_spec_runs_on_the_runner_python():
	assert f"{sys.version_info.major}.{sys.version_info.minor}" == RUNNER_PYTHON


def test_the_runner_packages_are_installed_at_their_versions():
	assert {name: importlib.metadata.version(name) for name in RUNNER_PACKAGES} == RUNNER_PACKAGES


def test_the_spec_imports_only_the_runner_packages():
	imported = set()
	for path in SPEC.rglob("*.py"):
		if path.name == "backend_inprocess.py":
			continue
		for node in ast.walk(ast.parse(path.read_text())):
			if isinstance(node, ast.Import):
				imported |= {alias.name.split(".")[0] for alias in node.names}
			elif isinstance(node, ast.ImportFrom) and node.level == 0:
				imported.add(node.module.split(".")[0])
	distributions = importlib.metadata.packages_distributions()
	third_party = {module for module in imported - set(sys.stdlib_module_names) if module != "files"}
	assert {module: distributions.get(module) for module in third_party if not set(distributions.get(module, [])) & set(RUNNER_PACKAGES)} == {}
