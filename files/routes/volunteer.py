
from files.__main__ import app
from files.classes.user import User
import files.helpers.jinja2
from files.helpers.wrappers import auth_required
from flask import render_template

@app.get("/volunteer")
@auth_required
def volunteer(v: User):
	return render_template("volunteer.html", v=v)


@files.helpers.jinja2.template_function
def volunteer_available_for(u: User) -> bool:
    return True
