from __future__ import annotations

import json
import sys
import threading
import time
from typing import TYPE_CHECKING

from flask import abort, g, request

from files.__main__ import app, db_session, limiter

if TYPE_CHECKING:
	from flask.wrappers import Response

# Track active requests for timeout monitoring
_active_requests = {}
_active_requests_lock = threading.Lock()
_monitor_thread = None

def start_request_monitor():
	"""Start a background thread to monitor for slow requests"""
	global _monitor_thread
	if _monitor_thread is None or not _monitor_thread.is_alive():
		_monitor_thread = threading.Thread(target=monitor_slow_requests, daemon=True)
		_monitor_thread.start()

def monitor_slow_requests():
	"""Background thread that checks for slow requests every 5 seconds"""
	while True:
		try:
			time.sleep(5)
			current_time = time.time()
			with _active_requests_lock:
				for request_id, info in list(_active_requests.items()):
					elapsed = current_time - info['start_time']
					# Log at 15 seconds (well before 30s timeout)
					if elapsed > 15 and not info.get('logged'):
						app.logger.warning(f"Slow request ({elapsed:.1f}s): {info['method']} {info['url']}")
						info['logged'] = True
		except Exception as e:
			app.logger.error(f"Error in request monitor: {e}")

# Start the monitor when the module loads
start_request_monitor()

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

	# Track this request for monitoring
	g.request_id = id(g)
	with _active_requests_lock:
		_active_requests[g.request_id] = {
			'start_time': g.start_time,
			'method': request.method,
			'url': request.url,
			'logged': False
		}


@app.teardown_appcontext
def teardown_request(error):
	# Clean up request tracking
	if hasattr(g, 'request_id'):
		with _active_requests_lock:
			_active_requests.pop(g.request_id, None)

	if hasattr(g, 'db') and g.db:
		g.db.close()
	sys.stdout.flush()

@app.after_request
def after_request(response: Response):
	# Remove from active requests (in case teardown doesn't run)
	if hasattr(g, 'request_id'):
		with _active_requests_lock:
			_active_requests.pop(g.request_id, None)

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
