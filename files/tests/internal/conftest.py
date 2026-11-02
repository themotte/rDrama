import pytest

from files.tests.spec.harness import backend


@pytest.fixture(autouse=True)
def isolated_state():
	backend.reset()
