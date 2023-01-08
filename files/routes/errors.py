import time

from http.client import responses
from urllib.parse import quote, urlencode

from flask import g, redirect, request, render_template, session

from files.__main__ import app
from files.helpers.const import ERROR_MESSAGES, WERKZEUG_ERROR_DESCRIPTIONS, SITE_FULL

@app.errorhandler(400)
@app.errorhandler(401)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(413)
@app.errorhandler(422)
@app.errorhandler(429)
def error(e):
	title = responses.get(e.code, "Internal Server Error")
	description = ERROR_MESSAGES.get(e.code, e.code)
	details = None if e.description == WERKZEUG_ERROR_DESCRIPTIONS.get(e.code, e.code) else e.description

	if request.headers.get("Authorization") or request.headers.get("xhr"): 
		return {"code": e.code, "description": description, "details": details, "error": title}, e.code
	
	return render_template('errors/error.html', err=True, code=e.code, error=title, description=description, details=details), e.code

@app.errorhandler(401)
def error_401(e):
	if request.headers.get("Authorization") or request.headers.get("xhr"): return error(e)
	path = request.path
	qs = urlencode(dict(request.values))
	argval = quote(f"{path}?{qs}", safe='')
	return redirect(f"/login?redirect={argval}")

@app.errorhandler(500)
def error_500(e):
	if getattr(g, 'db', None):
		g.db.rollback()
	else:
		app.logger.warning("Exception happened with no db initialized (perhaps early in request cycle?)")
	return error(e)

@app.post("/allow_nsfw")
def allow_nsfw():
	session["over_18"] = int(time.time()) + 3600
	redir = request.values.get("redir")
	if redir:
		if redir.startswith(f'{SITE_FULL}/'): return redirect(redir)
		if redir.startswith('/'): return redirect(f'{SITE_FULL}{redir}')
	return redirect('/')
