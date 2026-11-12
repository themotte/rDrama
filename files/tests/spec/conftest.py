import pytest

from files.tests.spec.harness import lifecycle


@pytest.fixture(autouse=True)
def isolated_state(request):
	if not request.config.pluginmanager.has_plugin("files.tests.spec.harness.plugin"):
		pytest.fail("the spec runs with its pytest plugin, files.tests.spec.harness.plugin (see its docstring), which this run didn't load", pytrace=False)
	profile = request.node.get_closest_marker("profile")
	lifecycle.begin(profile.args[0] if profile else None)
	yield
	lifecycle.end()
