import pytest

from files.tests.spec.harness import lifecycle


@pytest.fixture(autouse=True)
def isolated_state(request):
	profile = request.node.get_closest_marker("profile")
	lifecycle.begin(profile.args[0] if profile else None)
	yield
	lifecycle.end()
