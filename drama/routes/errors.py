from drama.helpers.wrappers import *
from drama.helpers.session import *
from drama.classes.custom_errors import *
from flask import *
from urllib.parse import quote, urlencode
import time
from drama.__main__ import app, r, cache, db_session
import gevent

# Errors




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

@app.errorhandler(PaymentRequired)
@auth_desired
@api()
def error_402(e, v):
	return{"html": lambda: (render_template('errors/402.html', v=v), 402),
		   "api": lambda: (jsonify({"error": "402 Payment Required"}), 402)
		   }

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


@app.errorhandler(413)
@auth_desired
@api()
def error_413(e, v):
	return{"html": lambda: (render_template('errors/413.html', v=v), 413),
		   "api": lambda: (jsonify({"error": "413 Request Payload Too Large"}), 413)
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


@app.route("/allow_nsfw_logged_in/<bid>", methods=["POST"])
@auth_required
@validate_formkey
def allow_nsfw_logged_in(bid, v):

	cutoff = int(time.time()) + 3600

	if not session.get("over_18", None):
		session["over_18"] = {}

	session["over_18"][bid] = cutoff

	return redirect(request.form.get("redir"))


@app.route("/allow_nsfw_logged_out/<bid>", methods=["POST"])
@auth_desired
def allow_nsfw_logged_out(bid, v):

	if v:
		return redirect('/')

	t = int(request.form.get('time'))

	if not validate_logged_out_formkey(t,
									   request.form.get("formkey")
									   ):
		abort(403)

	if not session.get("over_18", None):
		session["over_18"] = {}

	cutoff = int(time.time()) + 3600
	session["over_18"][bid] = cutoff

	return redirect(request.form.get("redir"))


@app.route("/allow_nsfl_logged_in/<bid>", methods=["POST"])
@auth_required
@validate_formkey
def allow_nsfl_logged_in(bid, v):

	cutoff = int(time.time()) + 3600

	if not session.get("show_nsfl", None):
		session["show_nsfl"] = {}

	session["show_nsfl"][bid] = cutoff

	return redirect(request.form.get("redir"))


@app.route("/allow_nsfl_logged_out/<bid>", methods=["POST"])
@auth_desired
def allow_nsfl_logged_out(bid, v):

	if v:
		return redirect('/')

	t = int(request.form.get('time'))

	if not validate_logged_out_formkey(t,
									   request.form.get("formkey")
									   ):
		abort(403)

	if not session.get("show_nsfl", None):
		session["show_nsfl"] = {}

	cutoff = int(time.time()) + 3600
	session["show_nsfl"][bid] = cutoff

	return redirect(request.form.get("redir"))


@app.route("/error/<eid>", methods=["GET"])
@auth_desired
def error_all_preview(eid, v):

	 eid=int(eid)
	 return render_template(f"errors/{eid}.html", v=v)

