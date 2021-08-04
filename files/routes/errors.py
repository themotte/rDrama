import jinja2.exceptions

from files.helpers.wrappers import *
from files.helpers.session import *
from flask import *
from urllib.parse import quote, urlencode
import time
from files.__main__ import app

# Errors



@app.errorhandler(400)
@auth_desired
def error_400(e, v):
	if request.headers.get("Authorization"): return {"error": "400 Bad Request"}, 400
	else: return render_template('errors/400.html', v=v), 400

@app.errorhandler(401)
def error_401(e):

	path = request.path
	qs = urlencode(dict(request.args))
	argval = quote(f"{path}?{qs}", safe='')
	output = f"/login?redirect={argval}"

	if request.headers.get("Authorization"): return {"error": "401 Not Authorized"}, 401
	else: return redirect(output)


@app.errorhandler(403)
@auth_desired
def error_403(e, v):
	if request.headers.get("Authorization"): return {"error": "403 Forbidden"}, 403
	else: return render_template('errors/403.html', v=v), 403


@app.errorhandler(404)
@auth_desired
def error_404(e, v):
	if request.headers.get("Authorization"): return {"error": "404 Not Found"}, 404
	else: return render_template('errors/404.html', v=v), 404


@app.errorhandler(405)
@auth_desired
def error_405(e, v):
	if request.headers.get("Authorization"): return {"error": "405 Method Not Allowed"}, 405
	else: return render_template('errors/405.html', v=v), 405


@app.errorhandler(409)
@auth_desired
def error_409(e, v):
	if request.headers.get("Authorization"): return {"error": "409 Conflict"}, 409
	else: return render_template('errors/409.html', v=v), 409


@app.errorhandler(410)
@auth_desired
def error_410(e, v):
	if request.headers.get("Authorization"): return {"error": "410 Request Payload Too Large"}, 410
	else: return render_template('errors/410.html', v=v), 410


@app.errorhandler(413)
@auth_desired
def error_413(e, v):
	if request.headers.get("Authorization"): return {"error": "413 Image Size Too Large"}, 413
	else: return render_template('errors/413.html', v=v), 413


@app.errorhandler(418)
@auth_desired
def error_418(e, v):
	if request.headers.get("Authorization"): return {"error": "418 I'm A Teapot"}, 418
	else: return render_template('errors/418.html', v=v), 418


@app.errorhandler(422)
@auth_desired
def error_422(e, v):
	if request.headers.get("Authorization"): return {"error": "422 Unprocessable Entity"}, 422
	else: return render_template('errors/422.html', v=v), 422


@app.errorhandler(429)
@auth_desired
def error_429(e, v):
	if request.headers.get("Authorization"): return {"error": "429 Too Many Requests"}, 429
	else: return render_template('errors/429.html', v=v), 429


@app.errorhandler(451)
@auth_desired
def error_451(e, v):
	if request.headers.get("Authorization"): return {"error": "451 Unavailable For Legal Reasons"}, 451
	else: return render_template('errors/451.html', v=v), 451


@app.errorhandler(500)
@auth_desired
def error_500(e, v):
	try:
		g.db.rollback()
	except AttributeError:
		pass

	if request.headers.get("Authorization"): return {"error": "500 Internal Server Error"}, 500
	else: return render_template('errors/500.html', v=v), 500


@app.errorhandler(502)
@auth_desired
def error_502(e, v):
	if request.headers.get("Authorization"): return {"error": "502 Bad Gateway"}, 502
	else: return render_template('errors/502.html', v=v), 502


@app.errorhandler(503)
@auth_desired
def error_503(e, v):
	if request.headers.get("Authorization"): return {"error": "503 Service Unavailable"}, 503
	else: return render_template('errors/503.html', v=v), 503



@app.post("/allow_nsfw")
def allow_nsfw():

	session["over_18"] = int(time.time()) + 3600

	return redirect(request.form.get("redir"))


@app.get("/error/<error>")
@auth_desired
def error_all_preview(error, v):

	try:
		return render_template(f"errors/{error}.html", v=v)
	except jinja2.exceptions.TemplateNotFound:
		abort(400)

