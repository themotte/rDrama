from __future__ import annotations

import json
import sys
import time
from typing import TYPE_CHECKING

from flask import abort, g, request

from files.__main__ import app, db_session, limiter

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

	limiter.check()

	g.db = db_session()


@app.teardown_appcontext
def teardown_request(error):
	if hasattr(g, 'db') and g.db:
		g.db.close()
	sys.stdout.flush()

@app.after_request
def after_request(response: Response):
	response.headers.add("Content-Security-Policy", ("""
		script-src 'self' https://*.googletagmanager.com;
		img-src https://*.google-analytics.com https://*.googletagmanager.com;
		connect-src 'self' https://*.google-analytics.com https://*.analytics.google.com https://*.googletagmanager.com;
		object-src 'none';
	"""))
	response.headers.add("Strict-Transport-Security", "max-age=31536000")
	response.headers.add("X-Frame-Options", "deny")
	return response
