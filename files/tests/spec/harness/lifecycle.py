'''Per-test setup and teardown for the spec tier.'''
from files.tests.spec.harness import backend, factories


def begin(profile: str | None):
	'''Puts the site back in its starting state, in deployment `profile` (one of config.PROFILES, or the default one when None).'''
	if not factories.has_signup_template():
		# In the default profile, where signing up straight after fetching the form isn't too soon
		backend.reset(None)
		factories.capture_signup_template()
	backend.reset(profile)


def end():
	log = backend.take_server_log()
	if log:
		# Shown beside the test's own output when it fails
		print(f"--- the implementation's log during this test ---\n{log}")
	attempts = backend.take_outbound_attempts()
	assert not attempts, f"the app attempted un-faked outbound connections: {attempts}"
