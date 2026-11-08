from datetime import datetime, timedelta
from typing import Optional

import sqlalchemy
from flask import abort, g, render_template, request

import files.helpers.jinja2
import files.routes.volunteer_janitor
from files.__main__ import app
from files.classes.user import User
from files.helpers.locks import volunteer_duty_lock
from files.helpers.wrappers import auth_required, refuse_api_client, refuse_while_suspended


@files.helpers.jinja2.template_function
def volunteer_available_for(u: Optional[User]) -> bool:
    return volunteer_get_duty(u) is not None

def volunteer_get_duty(u: Optional[User]) -> Optional[list[int]]:
    '''The ids of the comments `u` would be given to rate now, or None when there's nothing for them to do.'''
    if u is None or u.is_suspended or u.shadowbanned:
        return None
    
    if not app.config['DBG_VOLUNTEER_PERMISSIVE']:  # pragma: no branch (DBG_VOLUNTEER_PERMISSIVE relaxes the limits for trying duties out in development; outside the spec)
        # check to make sure it's at least 20h since the last volunteer
        if (u.volunteer_last_started_utc is not None) and (datetime.now() - u.volunteer_last_started_utc) < timedelta(hours = 20):
            return None
    
    return files.routes.volunteer_janitor.get_duty(u)


@app.get("/volunteer")
@auth_required
def volunteer(v: User):
    refuse_api_client(v)
    # Visits by one volunteer take turns, so a later one sees the duty an earlier one gave
    volunteer_duty_lock(g.db, v.id)
    g.db.refresh(v, ["volunteer_last_started_utc"])
    duty = volunteer_get_duty(v)

    assignments = None
    if duty is not None:
        assignments = files.routes.volunteer_janitor.assigned_comments(files.routes.volunteer_janitor.accept(v, duty))
        v.volunteer_last_started_utc = sqlalchemy.func.now()
        g.db.add(v)
        g.db.commit()

    return render_template("volunteer.html", v=v, assignments=assignments)

@app.post("/volunteer/submit")
@auth_required
def volunteer_submit(v: User):
    refuse_api_client(v)
    refuse_while_suspended(v)
    ratings = {}
    for k in request.form:
        if not k.startswith("volunteer-"):
            continue
        k_processed = k.removeprefix("volunteer-")
        values = request.form.getlist(k)
        if not k_processed.startswith("assignment-") or len(values) != 1:
            abort(400)
        ratings[k_processed.removeprefix("assignment-")] = values[0]

    files.routes.volunteer_janitor.submitted(v, ratings)
    return render_template("volunteer_submit.html", v=v)
