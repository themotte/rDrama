'''
The backend the harness drives the implementation through: backend_process when RDRAMA_SPEC_BACKEND is "process" (an implementation running in its own processes, which its launch commands start), otherwise backend_inprocess (the Python implementation, in the test's own process).
'''
import os

if os.environ.get("RDRAMA_SPEC_BACKEND") == "process":
	from files.tests.spec.harness.backend_process import *  # noqa: F403
else:
	from files.tests.spec.harness.backend_inprocess import *  # noqa: F403
