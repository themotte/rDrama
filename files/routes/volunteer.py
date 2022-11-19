
from datetime import datetime, timedelta
from files.__main__ import app
from files.classes.user import User
import files.helpers.jinja2
from files.helpers.wrappers import auth_required
from flask import render_template, g
import sqlalchemy
from typing import Optional

from files.routes.volunteer_common import VolunteerDuty
import files.routes.volunteer_janitor

@files.helpers.jinja2.template_function
def volunteer_available_for(u: Optional[User]) -> bool:
    return volunteer_get_duty(u) is not None

def volunteer_get_duty(u: Optional[User]) -> Optional[VolunteerDuty]:
    if u is None:
        return None
    
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
        duty.accept()
        v.volunteer_last_started_utc = sqlalchemy.func.now()
        g.db.add(v)
        g.db.commit()

    return render_template("volunteer.html", v=v, duty=duty)
