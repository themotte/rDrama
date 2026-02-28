import signal
import sys
import time
from gunicorn import glogging


# Gunicorn configuration
timeout = 90  # Worker heartbeat timeout - must exceed max request duration
graceful_timeout = 60  # Grace period for workers to finish after receiving SIGTERM


def post_worker_init(worker):
	"""Runs in each worker process after init. Installs a SIGABRT handler
	that dumps active requests before the worker dies on timeout."""
	import os
	import faulthandler

	def _abort_handler(signum, frame):
		try:
			from files.__main__ import active_requests
			now = time.time()
			if active_requests:
				for tid, (method, path, start) in active_requests.items():
					elapsed = now - start
					print(f"[worker-timeout] {elapsed:.1f}s: {method} {path} (thread {tid})",
						file=sys.stderr, flush=True)
			else:
				print("[worker-timeout] no active requests", file=sys.stderr, flush=True)
		except Exception as e:
			print(f"[worker-timeout] failed to dump: {e}", file=sys.stderr, flush=True)

		# Dump thread tracebacks (replaces faulthandler's SIGABRT handler)
		faulthandler.dump_traceback(file=sys.stderr, all_threads=True)

		# Re-raise with default handler to actually abort
		signal.signal(signal.SIGABRT, signal.SIG_DFL)
		os.kill(os.getpid(), signal.SIGABRT)

	signal.signal(signal.SIGABRT, _abort_handler)

# Access logging configuration
accesslog = 'logs/access.log'
access_log_format = '%({X-Real-IP}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
# Format explanation:
# %({X-Real-IP}i)s - Real client IP from X-Real-IP header (set by nginx proxy)
# %(l)s - '-' (remote log name, usually just a dash)
# %(u)s - User name (from HTTP auth, usually just a dash)
# %(t)s - Date/time of request
# %(r)s - Request line (method, path, protocol)
# %(s)s - Status code
# %(b)s - Response length in bytes
# %(f)s - Referer header
# %(a)s - User agent
# %(D)s - Request time in microseconds
