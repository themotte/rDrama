from flask import g

from files.__main__ import app, limiter
from files.classes.visstate import StateReport
from files.helpers.get import *
from files.helpers.sanitize import filter_emojis_only
from files.helpers.wrappers import *


REASON_LENGTH_MAXIMUM = 100


def _reason() -> str:
	'''The request's report reason, rendered: its first characters, up to the limit.'''
	return filter_emojis_only(request.values.get("reason", "").strip()[:REASON_LENGTH_MAXIMUM])


@app.post("/report/post/<pid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def api_flag_post(pid, v):
	post = get_post(pid)
	if post.is_draft_hidden_from(v): abort(404)
	reason = _reason()

	if reason.startswith('!') and v.admin_level >= 2:
		post.flair = reason[1:]
		g.db.add(post)
		ma=ModAction(
			kind="flair_post",
			user_id=v.id,
			target_submission_id=post.id,
			_note=f'"{post.flair}"'
		)
		g.db.add(ma)
	else:
		g.db.add(Flag(post_id=post.id, user_id=v.id, reason=reason))
		if v.reports_count:
			g.db.query(Submission) \
				.where(Submission.id == post.id, Submission.state_report != StateReport.IGNORED) \
				.update({Submission.state_report: StateReport.REPORTED})

	g.db.commit()

	return {"message": "Post reported!"}


@app.post("/report/comment/<cid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def api_flag_comment(cid, v):
	comment = get_comment(cid)
	if not comment.is_open_to(v): abort(404)
	reason = _reason()

	g.db.add(CommentFlag(comment_id=comment.id, user_id=v.id, reason=reason))
	if v.reports_count:
		g.db.query(Comment) \
			.where(Comment.id == comment.id, Comment.state_report != StateReport.IGNORED) \
			.update({Comment.state_report: StateReport.REPORTED})

	g.db.commit()

	return {"message": "Comment reported!"}
