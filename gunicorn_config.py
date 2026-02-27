import signal
import sys
import time
from gunicorn import glogging


# Gunicorn configuration
timeout = 90  # Worker heartbeat timeout - must exceed max request duration
graceful_timeout = 60  # Grace period for workers to finish after receiving SIGTERM


def worker_abort(worker):
	"""Called in the worker process when Gunicorn is about to kill it for timeout."""
	try:
		from files.__main__ import active_requests
		now = time.time()
		for tid, (method, path, start) in active_requests.items():
			elapsed = now - start
			print(f"[worker-timeout] {elapsed:.1f}s: {method} {path} (thread {tid})",
				file=sys.stderr, flush=True)
	except Exception as e:
		print(f"[worker-timeout] failed to dump active requests: {e}",
			file=sys.stderr, flush=True)

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
