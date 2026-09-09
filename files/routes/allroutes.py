from __future__ import annotations

import json
import sys
import threading
import time
from typing import TYPE_CHECKING

from flask import abort, g, request, session

from files.__main__ import app, db_session, limiter, is_known_bot, active_requests
from files.helpers.config.const import LOGGED_IN_COOKIE

if TYPE_CHECKING:
	from flask.wrappers import Response

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

	# Apply stricter rate limits for known bots (12 requests/minute ~= 1 every 5s)
	if is_known_bot():
		try:
			user_agent = request.headers.get('User-Agent', 'unknown')
			with limiter.limit("12/minute", key_func=lambda: f"bot-{user_agent}"):
				pass  # Just enforce the limit check
		except Exception:
			abort(429, "Rate limit exceeded for bots")

	# Create a new session instead of reusing the thread-local scoped session
	# This prevents thread safety issues with Gunicorn's gthread workers
	g.db = db_session.session_factory()
	g.start_time = time.time()
	active_requests[threading.get_ident()] = (request.method, request.full_path, g.start_time)


@app.teardown_appcontext
def teardown_request(error):
	active_requests.pop(threading.get_ident(), None)
	if hasattr(g, 'db') and g.db:
		g.db.close()
	sys.stdout.flush()

@app.after_request
def after_request(response: Response):
	if not app.debug and hasattr(g, 'start_time'):
		from files.__main__ import _perf, SLOW_THRESHOLD
		elapsed = time.time() - g.start_time
		route = f"{request.method} {request.full_path}"
		detail = route
		if request.form:
			safe_form = {k: v for k, v in request.form.items()
				if k.lower() not in ('password', 'secret', 'formkey')}
			if safe_form:
				detail += f" form={safe_form}"
		_perf.record_http(elapsed, detail, request.headers.get("User-Agent", ""))
		if elapsed >= SLOW_THRESHOLD:
			detail = route
			if request.form:
				safe_form = {k: v for k, v in request.form.items()
					if k.lower() not in ('password', 'secret', 'formkey')}
				detail += f" form={safe_form}"
			queries = getattr(g, 'query_count', 0)
			query_time = getattr(g, 'query_time', 0.0)
			ip = request.headers.get('X-Real-IP', request.remote_addr or '-')
			print(f"[slow-request] {elapsed:.1f}s ({queries} queries, {query_time:.1f}s in sql) ip={ip}: {detail}",
				file=sys.stderr, flush=True)

	# Keep the logged-in marker cookie in step with the session: set once when a member appears, deleted on the response that logs them out. Only for requests that already touched the session; reading it here would add Vary: Cookie to static responses that never look at it.
	if session.accessed:
		has_marker = LOGGED_IN_COOKIE in request.cookies
		cookie_attrs = dict(secure=app.config["SESSION_COOKIE_SECURE"], httponly=True, samesite=app.config["SESSION_COOKIE_SAMESITE"])
		if session.get("lo_user") and not has_marker:
			response.set_cookie(LOGGED_IN_COOKIE, "1", max_age=app.config["PERMANENT_SESSION_LIFETIME"], **cookie_attrs)
		elif has_marker and not session.get("lo_user"):
			response.delete_cookie(LOGGED_IN_COOKIE, **cookie_attrs)

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
