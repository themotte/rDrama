import jinja2.exceptions

from drama.helpers.wrappers import *
from drama.helpers.session import *
from flask import *
from urllib.parse import quote, urlencode
import time
from drama.__main__ import app

# Errors



@app.errorhandler(400)
@auth_desired
@api()
def error_400(e, v):
	return{"html": lambda: (render_template('errors/400.html', v=v), 400),
		   "api": lambda: (jsonify({"error": "400 Bad Request"}), 400	)
		   }


@app.errorhandler(401)
def error_401(e):

	path = request.path
	qs = urlencode(dict(request.args))
	argval = quote(f"{path}?{qs}", safe='')
	output = f"/login?redirect={argval}"

	if request.path.startswith("/api/v1/"):
		return jsonify({"error": "401 Not Authorized"}), 401
	else:
		return redirect(output)


@app.errorhandler(403)
@auth_desired
@api()
def error_403(e, v):
	return{"html": lambda: (render_template('errors/403.html', v=v), 403),
		   "api": lambda: (jsonify({"error": "403 Forbidden"}), 403)
		   }


@app.errorhandler(404)
@auth_desired
@api()
def error_404(e, v):
	return{"html": lambda: (render_template('errors/404.html', v=v), 404),
		   "api": lambda: (jsonify({"error": "404 Not Found"}), 404)
		   }


@app.errorhandler(405)
@auth_desired
@api()
def error_405(e, v):
	return{"html": lambda: (render_template('errors/405.html', v=v), 405),
		   "api": lambda: (jsonify({"error": "405 Method Not Allowed"}), 405)
		   }


@app.errorhandler(409)
@auth_desired
@api()
def error_409(e, v):
	return{"html": lambda: (render_template('errors/409.html', v=v), 409),
		   "api": lambda: (jsonify({"error": "409 Conflict"}), 409)
		   }


@app.errorhandler(410)
@auth_desired
@api()
def error_410(e, v):
	return{"html": lambda: (render_template('errors/410.html', v=v), 410),
		   "api": lambda: (jsonify({"error": "410 Request Payload Too Large"}), 410)
		   }

@app.errorhandler(413)
@auth_desired
@api()
def error_413(e, v):
	return{"html": lambda: (render_template('errors/413.html', v=v), 413),
		   "api": lambda: (jsonify({"error": "413 Image Size Too Large"}), 413)
		   }

@app.errorhandler(418)
@auth_desired
@api()
def error_418(e, v):
	return{"html": lambda: (render_template('errors/418.html', v=v), 418),
		   "api": lambda: (jsonify({"error": "418 I'm A Teapot"}), 418)
		   }


@app.errorhandler(422)
@auth_desired
@api()
def error_422(e, v):
	return{"html": lambda: (render_template('errors/422.html', v=v), 422),
		   "api": lambda: (jsonify({"error": "422 Unprocessable Entity"}), 422)
		   }


@app.errorhandler(429)
@auth_desired
@api()
def error_429(e, v):
	return{"html": lambda: (render_template('errors/429.html', v=v), 429),
		   "api": lambda: (jsonify({"error": "429 Too Many Requests"}), 429)
		   }


@app.errorhandler(451)
@auth_desired
@api()
def error_451(e, v):
	return{"html": lambda: (render_template('errors/451.html', v=v), 451),
		   "api": lambda: (jsonify({"error": "451 Unavailable For Legal Reasons"}), 451)
		   }


@app.errorhandler(500)
@auth_desired
@api()
def error_500(e, v):
	try:
		g.db.rollback()
	except AttributeError:
		pass

	return{"html": lambda: (render_template('errors/500.html', v=v), 500),
		   "api": lambda: (jsonify({"error": "500 Internal Server Error"}), 500)
		   }


@app.errorhandler(502)
@auth_desired
@api()
def error_502(e, v):
	return{"html": lambda: (render_template('errors/502.html', v=v), 502),
		   "api": lambda: (jsonify({"error": "502 Bad Gateway"}), 502)
		   }


@app.errorhandler(503)
@auth_desired
@api()
def error_503(e, v):
	return{"html": lambda: (render_template('errors/503.html', v=v), 503),
		   "api": lambda: (jsonify({"error": "503 Service Unavailable"}), 503)
		   }


@app.route("/allow_nsfw", methods=["POST"])
def allow_nsfw():

	session["over_18"] = int(time.time()) + 3600

	return redirect(request.form.get("redir"))


@app.route("/error/<error>", methods=["GET"])
@auth_desired
def error_all_preview(error, v):

	try:
		return render_template(f"errors/{error}.html", v=v)
	except jinja2.exceptions.TemplateNotFound:
		abort(400)

