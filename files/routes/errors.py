from files.helpers.wrappers import *
from flask import *
from urllib.parse import quote, urlencode
import time
from files.__main__ import app, limiter



@app.errorhandler(400)
def error_400(e):
	if request.headers.get("Authorization") or request.headers.get("xhr"): return {"error": "400 Bad Request"}, 400
	else: return render_template('errors/400.html', err=True), 400

@app.errorhandler(401)
def error_401(e):

	if request.headers.get("Authorization") or request.headers.get("xhr"): return {"error": "401 Not Authorized"}, 401
	else:
		path = request.path
		qs = urlencode(dict(request.values))
		argval = quote(f"{path}?{qs}", safe='')
		return redirect(f"/login?redirect={argval}")

@app.errorhandler(403)
def error_403(e):

	description = e.description
	if description == "You don't have the permission to access the requested resource. It is either read-protected or not readable by the server.": description = ''
	
	if request.headers.get("Authorization") or request.headers.get("xhr"):
		if not description: description = "403 Forbidden"
		return {"error": description}, 403
	else:
		if not description: description = "YOU AREN'T WELCOME HERE GO AWAY"
		return render_template('errors/403.html', description=description, err=True), 403


@app.errorhandler(404)
def error_404(e):
	if request.headers.get("Authorization") or request.headers.get("xhr"): return {"error": "404 Not Found"}, 404
	else: return render_template('errors/404.html', err=True), 404

@app.errorhandler(405)
def error_405(e):
	if request.headers.get("Authorization") or request.headers.get("xhr"): return {"error": "405 Method Not Allowed"}, 405
	else: return render_template('errors/405.html', err=True), 405

@app.errorhandler(413)
def error_413(e):
	return {"error": "Max file size is 8 MB (16 MB for paypigs)"}, 413
	if request.headers.get("Authorization") or request.headers.get("xhr"):
		return {"error": "Max file size is 8 MB (16 MB for paypigs)"}, 413
	else: return render_template('errors/413.html', err=True), 413

@app.errorhandler(429)
def error_429(e):
	if request.headers.get("Authorization") or request.headers.get("xhr"): return {"error": "429 Too Many Requests"}, 429
	else: return render_template('errors/429.html', err=True), 429


@app.errorhandler(500)
def error_500(e):
	g.db.rollback()

	if request.headers.get("Authorization") or request.headers.get("xhr"): return {"error": "500 Internal Server Error"}, 500
	else: return render_template('errors/500.html', err=True), 500


@app.post("/allow_nsfw")
def allow_nsfw():
	session["over_18"] = int(time.time()) + 3600
	redir = request.values.get("redir")
	if redir:
		if redir.startswith(f'{SITE_FULL}/'): return redirect(redir)
		if redir.startswith('/'): return redirect(f'{SITE_FULL}{redir}')
	return redirect('/')