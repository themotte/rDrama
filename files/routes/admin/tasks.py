from datetime import time
from typing import Optional

from flask import abort, g, redirect, render_template, request

import files.helpers.validators as validators
from files.__main__ import app
from files.classes.cron.scheduler import DayOfWeek, RepeatableTask, ScheduledTaskType
from files.classes.cron.submission import ScheduledSubmissionTemplate
from files.classes.user import User
from files.helpers.const import PERMS, SUBMISSION_FLAIR_LENGTH_MAXIMUM
from files.helpers.wrappers import admin_level_required


@app.get('/tasks/scheduled_posts/')
@admin_level_required(PERMS['SCHEDULED_POSTS'])
def tasks_scheduled_posts_get(v:User):
	submissions:list[ScheduledSubmissionTemplate] = \
		g.db.query(ScheduledSubmissionTemplate).all()
	return render_template("admin/tasks/scheduled_posts.html", v=v, listing=submissions)


def _get_request_bool(name:str) -> bool:
	return bool(request.values.get(name, default=False, type=bool))


def _get_request_dayofweek() -> DayOfWeek:
	week:DayOfWeek = DayOfWeek.NONE
	if _get_request_bool('schedule_day_sunday'): week |= DayOfWeek.SUNDAY
	if _get_request_bool('schedule_day_monday'): week |= DayOfWeek.MONDAY
	if _get_request_bool('schedule_day_tuesday'): week |= DayOfWeek.TUESDAY
	if _get_request_bool('schedule_day_wednesday'): week |= DayOfWeek.WEDNESDAY
	if _get_request_bool('schedule_day_thursday'): week |= DayOfWeek.THURSDAY
	if _get_request_bool('schedule_day_friday'): week |= DayOfWeek.FRIDAY
	if _get_request_bool('schedule_day_saturday'): week |= DayOfWeek.SATURDAY
	return week


@app.post('/tasks/scheduled_posts/')
@admin_level_required(PERMS['SCHEDULED_POSTS'])
def tasks_scheduled_posts_post(v:User):
	validated_post:validators.ValidatedSubmissionLike = \
		validators.ValidatedSubmissionLike.from_flask_request(request, 
			allow_embedding=app.config['MULTIMEDIA_EMBEDDING_ENABLED']
		)
	
	# first build the template
	flair:str=validators.guarded_value("flair", min_len=0, max_len=SUBMISSION_FLAIR_LENGTH_MAXIMUM)
	
	template:ScheduledSubmissionTemplate = ScheduledSubmissionTemplate(
		author_id=v.id, # TODO: allow customization
		ghost=_get_request_bool("ghost"),
		private=_get_request_bool("private"),
		over_18=_get_request_bool("over_18"),
		is_bot=False, # TODO: do we need this?
		title=validated_post.title,
		url=validated_post.url,
		body=validated_post.body,
		body_html=validated_post.body_html,
		flair=flair,
		embed_url=validated_post.embed_slow,
	)
	g.db.add(template)
	g.db.flush()

	# and then build the schedule
	enabled:bool = _get_request_bool('enabled')
	frequency_day:DayOfWeek = _get_request_dayofweek()
	hour:int = validators.int_ranged('hour', 0, 23)
	minute:int = validators.int_ranged('minute', 0, 59)
	second:int = 0 # TODO: seconds?

	time_of_day_utc:time = time(hour, minute, second)

	# and then build the scheduled task
	task:RepeatableTask = RepeatableTask(
		author_id=v.id,
		type_id=int(ScheduledTaskType.SCHEDULED_SUBMISSION),
		data_id=template.id,
		enabled=enabled,
		frequency_day=int(frequency_day),
		time_of_day_utc=time_of_day_utc,
	)
	g.db.add(task)
	g.db.commit()
	return redirect(f'/tasks/scheduled_posts/{template.id}')

@app.get('/tasks/scheduled_posts/<int:pid>')
@admin_level_required(PERMS['SCHEDULED_POSTS'])
def tasks_scheduled_post_get(v:User, pid:int):
	submission: Optional[ScheduledSubmissionTemplate] = \
		g.db.get(ScheduledSubmissionTemplate, pid)
	if not submission: abort(404)
	return render_template("admin/tasks/scheduled_post.html", v=v, p=submission)
