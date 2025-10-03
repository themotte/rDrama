from __future__ import annotations

import json
import signal
import sys
import time
from typing import TYPE_CHECKING

from flask import abort, g, request

from files.__main__ import app, db_session, limiter

if TYPE_CHECKING:
	from flask.wrappers import Response

# Track current request for timeout monitoring (single-threaded sync workers)
_current_request_info = None

def setup_slow_request_alarm():
	"""Set up SIGALRM handler to log slow requests before timeout"""
	def alarm_handler(signum, frame):
		"""Called when alarm goes off - logs slow request"""
		if _current_request_info:
			print(f"[SLOW REQUEST] 15s alarm: {_current_request_info['method']} {_current_request_info['url']}", file=sys.stderr)
			sys.stderr.flush()
			app.logger.warning(f"Slow request (15s): {_current_request_info['method']} {_current_request_info['url']}")
		else:
			print(f"[SLOW REQUEST] 15s alarm: no request info", file=sys.stderr)
			sys.stderr.flush()

	signal.signal(signal.SIGALRM, alarm_handler)

# Set up the alarm handler when module loads
setup_slow_request_alarm()

@app.before_request
def before_request():
	with open('site_settings.json', 'r') as f:
		app.config['SETTINGS'] = json.load(f)

	if request.host != app.config["SERVER_NAME"]:
		return {"error": "Unauthorized host provided."}, 403

	if not app.config['SETTINGS']['Bots'] and request.headers.get("Authorization"):
		abort(403, "Bots are currently not allowed")

	g.agent = request.headers.get("User-Agent")
	if not g.agent:
		return 'Please use a "User-Agent" header!', 403

	ua = g.agent.lower()
	g.debug = app.debug
	g.webview = ('; wv) ' in ua)
	g.inferior_browser = (
		'iphone' in ua or
		'ipad' in ua or
		'ipod' in ua or
		'mac os' in ua or
		' firefox/' in ua)
	g.timestamp = int(time.time())

	limiter.check()

	g.db = db_session()
	g.start_time = time.time()

	# Track this request and set alarm for 15 seconds
	global _current_request_info
	_current_request_info = {
		'start_time': g.start_time,
		'method': request.method,
		'url': request.url,
	}

	# Set alarm for 15 seconds (before the 30s gunicorn timeout)
	signal.alarm(15)


@app.teardown_appcontext
def teardown_request(error):
	# Cancel the alarm since request is done
	signal.alarm(0)

	# Clean up request tracking
	global _current_request_info
	_current_request_info = None

	if hasattr(g, 'db') and g.db:
		g.db.close()
	sys.stdout.flush()

@app.after_request
def after_request(response: Response):
	# Cancel the alarm since request completed successfully
	signal.alarm(0)

	# Clean up request tracking
	global _current_request_info
	_current_request_info = None

	response.headers.add("Content-Security-Policy", ("""
		script-src 'self' 'unsafe-inline' https://*.googletagmanager.com https://hcaptcha.com https://*.hcaptcha.com;
		img-src 'self' https://*.google-analytics.com https://*.googletagmanager.com;
		connect-src 'self' https://*.google-analytics.com https://*.analytics.google.com https://*.googletagmanager.com https://hcaptcha.com https://*.hcaptcha.com;
		object-src 'none';
		frame-src https://hcaptcha.com https://*.hcaptcha.com;
		style-src 'self' 'unsafe-inline' https://hcaptcha.com https://*.hcaptcha.com;
	""".replace('\n', '').replace('\t', ' ')))
	response.headers.add("Strict-Transport-Security", "max-age=31536000")
	response.headers.add("X-Frame-Options", "deny")
	return response
