import signal
import sys
import threading
from gunicorn import glogging


# Gunicorn configuration
timeout = 30  # Worker timeout in seconds
graceful_timeout = 5  # Grace period for workers to finish after receiving SIGTERM

# Thread-local storage for current request in each worker
_current_request = threading.local()


class CustomLogger(glogging.Logger):
	"""Custom logger - currently just passes through to base class"""
	pass


# Set the custom logger class
logger_class = CustomLogger


def when_ready(server):
	"""Called just after the server is started"""
	server.log.info("Server is ready. Spawning workers")


def worker_int(worker):
	"""Called just after a worker exited on SIGINT or SIGQUIT"""
	worker.log.info(f"Worker {worker.pid} received SIGINT or SIGQUIT")


def pre_request(worker, req):
	"""Called just before a worker processes the request"""
	try:
		# Extract request info from the req object
		method = req.method if hasattr(req, 'method') else 'UNKNOWN'
		path = req.path if hasattr(req, 'path') else 'UNKNOWN'
		query = req.query if hasattr(req, 'query') else ''
		url = f"{path}?{query}" if query else path
		# Store in thread-local storage
		_current_request.value = f"{method} {url}"
		_current_request.worker = worker
	except Exception:
		pass


def post_request(worker, req, environ, resp):
	"""Called after a worker processes the request"""
	# Clear the request context
	_current_request.value = None
	_current_request.worker = None


def worker_abort(worker):
	"""Called when a worker receives SIGABRT signal (timeout)"""
	# This is called BEFORE the worker is killed, so we can log the current request
	request_info = getattr(_current_request, 'value', None)
	if request_info:
		worker.log.critical(f"WORKER TIMEOUT on request: {request_info}")
	else:
		worker.log.critical("WORKER TIMEOUT (no request info available)")


def post_worker_init(worker):
	"""Called just after a worker has initialized the application"""
	# Install custom signal handler to catch timeout before death
	def timeout_handler(signum, frame):
		"""Handle timeout signal by logging current request"""
		request_info = getattr(_current_request, 'value', None)
		if request_info:
			print(f"[TIMEOUT] Worker {worker.pid} timing out on request: {request_info}", file=sys.stderr)
			sys.stderr.flush()
		# Re-raise the signal to continue normal handling
		signal.signal(signal.SIGABRT, signal.SIG_DFL)
		# Use os.kill instead of raise_signal for Python 3.8+ compatibility
		import os
		os.kill(os.getpid(), signal.SIGABRT)

	# Install our handler for SIGABRT (Gunicorn's timeout signal)
	signal.signal(signal.SIGABRT, timeout_handler)
