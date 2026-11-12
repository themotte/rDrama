'''
The backend the harness drives the implementation through: backend_process (an implementation running in its own processes, which its launch commands start), unless RDRAMA_SPEC_BACKEND is "inprocess", which the current implementation's own runner sets to drive it in the test's own process; that backend isn't part of the spec.
'''
import os

_BACKEND = os.environ.get("RDRAMA_SPEC_BACKEND", "process")
if _BACKEND not in ("process", "inprocess"):
	raise RuntimeError(f"RDRAMA_SPEC_BACKEND names no backend: {_BACKEND!r} (\"process\", or \"inprocess\" for the current implementation's own)")
IN_PROCESS = _BACKEND == "inprocess"
'''Whether the implementation runs in the test's own process, rather than in processes of its own.'''
if IN_PROCESS:
	from files.tests.spec.harness.backend_inprocess import *  # noqa: F403
else:
	from files.tests.spec.harness.backend_process import *  # noqa: F403
