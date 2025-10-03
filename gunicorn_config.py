import signal
import sys
from gunicorn import glogging


# Gunicorn configuration
timeout = 30  # Worker timeout in seconds
graceful_timeout = 5  # Grace period for workers to finish after receiving SIGTERM

# Current request info (one request per worker in sync mode)
_current_request_info = None
_current_worker = None


def when_ready(server):
	"""Called just after the server is started"""
	print("Server is ready. Spawning workers")
	print("Server is ready. Spawning workers (STDERR)", file=sys.stderr)
	sys.stderr.flush()


def worker_int(worker):
	"""Called just after a worker exited on SIGINT or SIGQUIT"""
	print(f"Worker {worker.pid} received SIGINT or SIGQUIT")


def pre_request(worker, req):
	"""Called just before a worker processes the request"""
	global _current_request_info, _current_worker
	try:
		# Extract request info from the req object
		method = req.method if hasattr(req, 'method') else 'UNKNOWN'
		path = req.path if hasattr(req, 'path') else 'UNKNOWN'
		query = req.query if hasattr(req, 'query') else ''
		url = f"{path}?{query}" if query else path
		# Store in module-level variables
		_current_request_info = f"{method} {url}"
		_current_worker = worker
	except Exception:
		print("Failed to extract request")
		pass


def post_request(worker, req, environ, resp):
	"""Called after a worker processes the request"""
	global _current_request_info, _current_worker
	# Clear the request context
	_current_request_info = None
	_current_worker = None


def worker_abort(worker):
	"""Called when a worker receives SIGABRT signal (timeout)"""
	# This is called BEFORE the worker is killed, so we can log the current request
	print(f"[worker_abort] Called for worker {worker.pid}", file=sys.stderr)
	sys.stderr.flush()
	if _current_request_info:
		print(f"[worker_abort] WORKER TIMEOUT on request: {_current_request_info}", file=sys.stderr)
		sys.stderr.flush()
	else:
		print(f"[worker_abort] WORKER TIMEOUT (no request info available)", file=sys.stderr)
		sys.stderr.flush()

def post_worker_init(worker):
	"""Called just after a worker has initialized the application"""
	import os

	# Install custom signal handler to catch timeout before death
	def timeout_handler(signum, frame):
		"""Handle timeout signal by logging current request"""
		print(f"[timeout_handler] Signal {signum} received by worker {worker.pid}", file=sys.stderr)
		sys.stderr.flush()

		if _current_request_info:
			print(f"[timeout_handler] Worker {worker.pid} timing out on request: {_current_request_info}", file=sys.stderr)
			sys.stderr.flush()
		else:
			print(f"[timeout_handler] Worker {worker.pid} timing out (no request info available)", file=sys.stderr)
			sys.stderr.flush()

		print(f"[timeout_handler] Resetting signal handler and re-raising SIGABRT", file=sys.stderr)
		sys.stderr.flush()

		# Re-raise the signal to continue normal handling
		signal.signal(signal.SIGABRT, signal.SIG_DFL)
		os.kill(os.getpid(), signal.SIGABRT)

	# Install our handler for SIGABRT (Gunicorn's timeout signal)
	signal.signal(signal.SIGABRT, timeout_handler)

	print(f"Worker {worker.pid} initialized - SIGABRT handler installed", file=sys.stderr)
	sys.stderr.flush()

	# Verify the handler is installed
	current_handler = signal.getsignal(signal.SIGABRT)
	print(f"Worker {worker.pid} SIGABRT handler check: {current_handler}", file=sys.stderr)
	sys.stderr.flush()
