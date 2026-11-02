import pytest

from files.tests.spec.harness import lifecycle


@pytest.fixture(autouse=True)
def isolated_state():
	lifecycle.begin()
	yield
	lifecycle.end()
