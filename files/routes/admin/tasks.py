from datetime import time
from typing import Optional

from flask import abort, g, redirect, render_template, request

import files.helpers.validators as validators
from files.__main__ import app
from files.classes.cron.submission import ScheduledSubmissionTask
from files.classes.cron.tasks import (DayOfWeek, RepeatableTask,
                                      RepeatableTaskRun, ScheduledTaskType)
from files.classes.user import User
from files.helpers.config.const import PERMS, SUBMISSION_FLAIR_LENGTH_MAXIMUM
from files.helpers.config.environment import MULTIMEDIA_EMBEDDING_ENABLED
from files.helpers.wrappers import admin_level_required


def _modify_task_schedule(pid:int):
	task: Optional[RepeatableTask] = g.db.get(RepeatableTask, pid)
	if not task: abort(404)

	# rebuild the schedule
	task.enabled = _get_request_bool('enabled')
	task.frequency_day_flags = _get_request_dayofweek()
	hour:int = validators.int_ranged('hour', 0, 23)
	minute:int = validators.int_ranged('minute', 0, 59)
	second:int = 0 # TODO: seconds?

	time_of_day_utc:time = time(hour, minute, second)
	task.time_of_day_utc = time_of_day_utc
	g.db.commit()

@app.get('/tasks/')
@admin_level_required(PERMS['SCHEDULER'])
def tasks_get(v:User):
	tasks:list[RepeatableTask] = \
		g.db.query(RepeatableTask).all()
	return render_template("admin/tasks/tasks.html", v=v, listing=tasks)


@app.get('/tasks/<int:task_id>/')
@admin_level_required(PERMS['SCHEDULER'])
def tasks_get_task(v:User, task_id:int):
	task:RepeatableTask = g.db.get(RepeatableTask, task_id)
	if not task: abort(404)
	return render_template("admin/tasks/single_task.html", v=v, task=task)


@app.get('/tasks/<int:task_id>/runs/')
@admin_level_required(PERMS['SCHEDULER'])
def tasks_get_task_redirect(v:User, task_id:int): # pyright: ignore
	return redirect(f'/tasks/{task_id}/')


@app.get('/tasks/<int:task_id>/runs/<int:run_id>')
@admin_level_required(PERMS['SCHEDULER'])
def tasks_get_task_run(v:User, task_id:int, run_id:int):
	run:RepeatableTaskRun = g.db.get(RepeatableTaskRun, run_id)
	if not run: abort(404)
	if run.task_id != task_id:
		return redirect(f'/tasks/{run.task_id}/runs/{run.id}')
	return render_template("admin/tasks/single_run.html", v=v, run=run)


@app.post('/tasks/<int:task_id>/schedule')
@admin_level_required(PERMS['SCHEDULER'])
def task_schedule_post(v:User, task_id:int): # pyright: ignore
	_modify_task_schedule(task_id)
	return redirect(f'/tasks/{task_id}')


@app.get('/tasks/scheduled_posts/')
@admin_level_required(PERMS['SCHEDULER_POSTS'])
def tasks_scheduled_posts_get(v:User):
	submissions:list[ScheduledSubmissionTask] = \
		g.db.query(ScheduledSubmissionTask).all()
	return render_template("admin/tasks/scheduled_posts.html", v=v, listing=submissions)


def _get_request_bool(name:str) -> bool:
	return bool(request.values.get(name, default=False, type=bool))


def _get_request_dayofweek() -> DayOfWeek:
	days:DayOfWeek = DayOfWeek.NONE
	for day in DayOfWeek.all_days:
		name:str = day.name.lower()
		if _get_request_bool(f'schedule_day_{name}'): days |= day
	return days


@app.post('/tasks/scheduled_posts/')
@admin_level_required(PERMS['SCHEDULER_POSTS'])
def tasks_scheduled_posts_post(v:User):
	validated_post:validators.ValidatedSubmissionLike = \
		validators.ValidatedSubmissionLike.from_flask_request(request, 
			allow_embedding=MULTIMEDIA_EMBEDDING_ENABLED,
		)
	
	# first build the template
	flair:str = validators.guarded_value("flair", min_len=0, max_len=SUBMISSION_FLAIR_LENGTH_MAXIMUM)

	# and then build the schedule
	enabled:bool = _get_request_bool('enabled')
	frequency_day:DayOfWeek = _get_request_dayofweek()
	hour:int = validators.int_ranged('hour', 0, 23)
	minute:int = validators.int_ranged('minute', 0, 59)
	second:int = 0 # TODO: seconds?

	time_of_day_utc:time = time(hour, minute, second)

	# and then build the scheduled task
	task:ScheduledSubmissionTask = ScheduledSubmissionTask(
		author_id=v.id,
		author_id_submission=v.id, # TODO: allow customization
		enabled=enabled,
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
		frequency_day=int(frequency_day),
		time_of_day_utc=time_of_day_utc,
		type_id=int(ScheduledTaskType.SCHEDULED_SUBMISSION),
	)
	g.db.add(task)
	g.db.commit()
	return redirect(f'/tasks/scheduled_posts/{task.id}')


@app.get('/tasks/scheduled_posts/<int:pid>')
@admin_level_required(PERMS['SCHEDULER_POSTS'])
def tasks_scheduled_post_get(v:User, pid:int):
	submission: Optional[ScheduledSubmissionTask] = \
		g.db.get(ScheduledSubmissionTask, pid)
	if not submission: abort(404)
	return render_template("admin/tasks/scheduled_post.html", v=v, p=submission)


@app.post('/tasks/scheduled_posts/<int:pid>/content')
@admin_level_required(PERMS['SCHEDULER_POSTS'])
def task_scheduled_post_content_post(v:User, pid:int): # pyright: ignore
	submission: Optional[ScheduledSubmissionTask] = \
		g.db.get(ScheduledSubmissionTask, pid)
	if not submission: abort(404)
	if not v.can_edit(submission): abort(403)

	validated_post:validators.ValidatedSubmissionLike = \
		validators.ValidatedSubmissionLike.from_flask_request(request, 
			allow_embedding=MULTIMEDIA_EMBEDDING_ENABLED,
		)
	
	edited:bool = False
	if submission.body != validated_post.body:
		submission.body = validated_post.body
		submission.body_html = validated_post.body_html
		edited = True
	
	if submission.title != validated_post.title:
		submission.title = validated_post.title
		edited = True

	if not edited:
		abort(400, "Title or body must be edited")
	
	g.db.commit()
	return redirect(f'/tasks/scheduled_posts/{pid}')

@app.post('/tasks/scheduled_posts/<int:task_id>/schedule')
@admin_level_required(PERMS['SCHEDULER'])
def task_scheduled_post_post(v:User, task_id:int): # pyright: ignore
	# permission being SCHEDULER is intentional as SCHEDULER_POSTS is for
	# creating or editing post content
	_modify_task_schedule(task_id)
	return redirect(f'/tasks/scheduled_posts/{task_id}')
