from datetime import datetime, timedelta
from typing import Optional

import sqlalchemy
from flask import abort, g, render_template, request

import files.helpers.jinja2
import files.routes.volunteer_janitor
from files.__main__ import app
from files.classes.user import User
from files.helpers.wrappers import auth_required


@files.helpers.jinja2.template_function
def volunteer_available_for(u: Optional[User]) -> bool:
    return volunteer_get_duty(u) is not None

def volunteer_get_duty(u: Optional[User]) -> Optional[list[int]]:
    '''The ids of the comments `u` would be given to rate now, or None when there's nothing for them to do.'''
    if u is None:
        return None
    
    if not app.config['DBG_VOLUNTEER_PERMISSIVE']:
        # check to make sure it's at least 20h since the last volunteer
        if (u.volunteer_last_started_utc is not None) and (datetime.now() - u.volunteer_last_started_utc) < timedelta(hours = 20):
            return None
    
    return files.routes.volunteer_janitor.get_duty(u)


@app.get("/volunteer")
@auth_required
def volunteer(v: User):
    duty = volunteer_get_duty(v)

    if duty is not None:
        files.routes.volunteer_janitor.accept(v, duty)
        v.volunteer_last_started_utc = sqlalchemy.func.now()
        g.db.add(v)
        g.db.commit()

    return render_template("volunteer.html", v=v, comments=files.routes.volunteer_janitor.comments(duty) if duty else None)

@app.post("/volunteer/submit")
@auth_required
def volunteer_submit(v: User):
    for k in request.values:
        if not k.startswith("volunteer-"):
            continue
        k_processed = k.removeprefix("volunteer-")

        if k_processed.startswith("janitor-"):
            files.routes.volunteer_janitor.submitted(v, k_processed.removeprefix("janitor-"), request.values[k])
        else:
            abort(400)

    return render_template("volunteer_submit.html", v=v)
