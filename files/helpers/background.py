import threading
from contextlib import contextmanager

from files.helpers.config.environment import SPEC_TEST_MODE

# In test mode, spawned work is queued instead of started, so tests can run it deterministically via drain() and it can't outlive the test that caused it.
_deferred: list | None = [] if SPEC_TEST_MODE else None


def spawn_background(fn, *args):
	if _deferred is not None:
		_deferred.append((fn, args))
		return
	threading.Thread(target=fn, args=args, daemon=True).start()


def drain():
	while _deferred:
		fn, args = _deferred.pop(0)
		fn(*args)


def discard():
	if _deferred is not None:
		_deferred.clear()


@contextmanager
def separately():
	'''In test mode, work handed off inside the block runs by the time the block ends, while work held before it stays held: for standing in for a process of its own (a command, the scheduler), which does its own work before it exits.'''
	global _deferred
	if _deferred is None:
		yield
		return
	earlier, _deferred = _deferred, []
	try:
		yield
		drain()
	finally:
		_deferred = earlier
