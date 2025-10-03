import threading
from gunicorn import glogging


# Thread-local storage to track current request
_request_context = threading.local()


class CustomLogger(glogging.Logger):
	def critical(self, msg, *args, **kwargs):
		# If this is a worker timeout, append request info
		if 'WORKER TIMEOUT' in str(msg):
			current_request = getattr(_request_context, 'current_request', None)
			if current_request:
				msg = f"{msg} - Request: {current_request}"

		super().critical(msg, *args, **kwargs)


# Set the custom logger class
logger_class = CustomLogger


# Middleware to track requests
def pre_request(worker, req):
	"""Called just before a worker processes the request"""
	try:
		# Extract request info from the req object
		method = req.method if hasattr(req, 'method') else 'UNKNOWN'
		path = req.path if hasattr(req, 'path') else 'UNKNOWN'
		query = req.query if hasattr(req, 'query') else ''
		url = f"{path}?{query}" if query else path
		_request_context.current_request = f"{method} {url}"
	except Exception:
		_request_context.current_request = None


def post_request(worker, req, environ, resp):
	"""Called after a worker processes the request"""
	# Clear the request context
	_request_context.current_request = None
