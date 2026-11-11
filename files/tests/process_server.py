'''
The site in test mode for the out-of-process backend (spec/harness/backend_process.py): the application, behind the control requests that backend's interface describes. Served by `gunicorn files.tests.process_server:application`, in one process.
'''
import json
import os
import time
import traceback
import uuid
from datetime import datetime

from files.__main__ import app, db_session, limiter
from files.helpers import background
from files.helpers.config.environment import SPEC_TEST_MODE

if not SPEC_TEST_MODE:
	raise RuntimeError("the control requests hold and run background work only in test mode: set SPEC_TEST_MODE")

# The process id too, so a process forked from one that imported this module doesn't pass for it
BOOT = f"{os.getpid()}-{uuid.uuid4().hex}"


def _reset(body):
	background.discard()
	limiter.clock = time.time


def _clock(body):
	at = datetime.fromisoformat(body["at"])
	if at.tzinfo is None:
		raise ValueError(f"the time {body['at']!r} has no UTC offset")
	limiter.clock = lambda: at.timestamp()


_CONTROLS = {
	"/__spec__/ready": lambda body: None,
	"/__spec__/background/run": lambda body: background.drain(),
	"/__spec__/reset": _reset,
	"/__spec__/clock": _clock,
}


def application(environ, start_response):
	control = _CONTROLS.get(environ.get("PATH_INFO", ""))
	if control is None or environ["REQUEST_METHOD"] != "POST":
		return app(environ, start_response)
	try:
		raw = environ["wsgi.input"].read(int(environ.get("CONTENT_LENGTH") or 0))
		control(json.loads(raw) if raw else None)
		status, content_type, body = "200 OK", "application/json", json.dumps({"boot": BOOT}).encode()
	except Exception:
		status, content_type, body = "500 Internal Server Error", "text/plain; charset=utf-8", traceback.format_exc().encode()
	finally:
		# Background work may leave the thread's session holding a transaction; release it as a finished request does
		db_session.remove()
	start_response(status, [("Content-Type", content_type), ("Content-Length", str(len(body)))])
	return [body]
