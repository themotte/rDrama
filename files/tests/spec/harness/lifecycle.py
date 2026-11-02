'''Per-test setup and teardown for the spec tier.'''
from files.tests.spec.harness import backend, factories


def begin():
	backend.reset()
	if not factories.has_signup_template():
		factories.capture_signup_template()
		backend.reset()


def end():
	attempts = backend.take_outbound_attempts()
	assert not attempts, f"the app attempted un-faked outbound connections: {attempts}"
