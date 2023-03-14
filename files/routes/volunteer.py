
from datetime import datetime, timedelta
from typing import Optional

import sqlalchemy
from flask import abort, g, render_template, request

import files.helpers.jinja2
import files.routes.volunteer_janitor
from files.__main__ import app
from files.classes.user import User
from files.helpers.config.environment import DBG_VOLUNTEER_PERMISSIVE
from files.helpers.wrappers import auth_required
from files.routes.volunteer_common import VolunteerDuty


@files.helpers.jinja2.template_function
def volunteer_available_for(u: Optional[User]) -> bool:
    return volunteer_get_duty(u) is not None

def volunteer_get_duty(u: Optional[User]) -> Optional[VolunteerDuty]:
    if u is None:
        return None
    
    if not DBG_VOLUNTEER_PERMISSIVE:
        # check to make sure it's at least 20h since the last volunteer
        if (u.volunteer_last_started_utc is not None) and (datetime.now() - u.volunteer_last_started_utc) < timedelta(hours = 20):
            return None
    
    # TODO: clever code that figures out the most important duty available
    janitor = files.routes.volunteer_janitor.get_duty(u)
    if janitor is not None:
        return janitor
    
    # oh well
    return None


@app.get("/volunteer")
@auth_required
def volunteer(v: User):
    duty = volunteer_get_duty(v)

    if duty is not None:
        duty.accept(v)
        v.volunteer_last_started_utc = sqlalchemy.func.now()
        g.db.add(v)
        g.db.commit()

    return render_template("volunteer.html", v=v, duty=duty)

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
