import threading
from gunicorn import glogging


# Thread-local storage to track current request
_request_context = threading.local()


def set_current_request(environ):
	"""Store current request info in thread-local storage"""
	try:
		method = environ.get('REQUEST_METHOD', '')
		path = environ.get('PATH_INFO', '')
		query = environ.get('QUERY_STRING', '')
		url = f"{path}?{query}" if query else path
		_request_context.current_request = f"{method} {url}"
	except Exception:
		_request_context.current_request = None


def get_current_request():
	"""Get current request from thread-local storage"""
	return getattr(_request_context, 'current_request', None)


class CustomLogger(glogging.Logger):
	def critical(self, msg, *args, **kwargs):
		# If this is a worker timeout, append request info
		if 'WORKER TIMEOUT' in str(msg):
			current_request = get_current_request()
			if current_request:
				msg = f"{msg} - Request: {current_request}"

		super().critical(msg, *args, **kwargs)


# Set the custom logger class
logger_class = CustomLogger


# Middleware to track requests
def pre_request(worker, req):
	"""Called just before a worker processes the request"""
	set_current_request(req.environ)


def post_request(worker, req, environ, resp):
	"""Called after a worker processes the request"""
	# Clear the request context
	_request_context.current_request = None
