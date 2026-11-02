import os
import threading

# In test mode, spawned work is queued instead of started, so tests can run it deterministically via drain() and it can't outlive the test that caused it.
_deferred: list | None = [] if os.environ.get("RDRAMA_TESTING") == "1" else None


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
