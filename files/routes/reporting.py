from flask import g

from files.__main__ import app, limiter
from files.classes.visstate import StateReport
from files.helpers.get import *
from files.helpers.sanitize import filter_emojis_only
from files.helpers.wrappers import *


REASON_LENGTH_MAXIMUM = 100
REASON_RENDERED_LENGTH_MAXIMUM = 350 # what the reports' reason columns hold
FLAIR_RENDERED_LENGTH_MAXIMUM = 254 # what the mod log's note holds, with the quotes around it


def _reason(limit: int) -> str:
	'''The request's report reason, rendered: its first characters, as many as fit rendered into `limit` characters.'''
	reason = request.values.get("reason", "").strip()[:REASON_LENGTH_MAXIMUM]
	while len(rendered := filter_emojis_only(reason)) > limit: reason = reason[:-1]
	return rendered


@app.post("/report/post/<pid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def api_flag_post(pid, v):
	post = get_post(pid)
	if post.is_draft_hidden_from(v): abort(404)
	reason = _reason(REASON_RENDERED_LENGTH_MAXIMUM)

	if reason.startswith('!') and v.admin_level >= 2:
		post.flair = _reason(FLAIR_RENDERED_LENGTH_MAXIMUM + 1)[1:]
		g.db.add(post)
		ma=ModAction(
			kind="flair_post",
			user_id=v.id,
			target_submission_id=post.id,
			_note=f'"{post.flair}"'
		)
		g.db.add(ma)
	else:
		flag = Flag(post_id=post.id, user_id=v.id, reason=reason)
		g.db.add(flag)

		# We only want to notify if the user is not permabanned
		if not v.is_suspended_permanently:
			g.db.query(Submission) \
				.where(Submission.id == post.id, Submission.state_report != StateReport.IGNORED) \
				.update({Submission.state_report: StateReport.REPORTED})

	g.db.commit()

	return {"message": "Post reported!"}


@app.post("/report/comment/<cid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def api_flag_comment(cid, v):

	# I'm not hugely into blocking this entirely, really we should be recording it and then mostly ignoring it, but whatever
	if not v.is_suspended_permanently and not v.shadowbanned:
		comment = get_comment(cid)
		if not comment.is_open_to(v): abort(404)
		reason = _reason(REASON_RENDERED_LENGTH_MAXIMUM)

		flag = CommentFlag(comment_id=comment.id, user_id=v.id, reason=reason)
		g.db.add(flag)

		g.db.query(Comment) \
				.where(Comment.id == comment.id, Comment.state_report != StateReport.IGNORED) \
				.update({Comment.state_report: StateReport.REPORTED})
		
		g.db.commit()

	return {"message": "Comment reported!"}
