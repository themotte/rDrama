from files.helpers.wrappers import *
from files.helpers.get import *
from flask import g
from files.__main__ import app, limiter
from files.helpers.sanitize import filter_emojis_only

@app.post("/report/post/<pid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def api_flag_post(pid, v):

	post = get_post(pid)
	reason = request.values.get("reason", "").strip()[:100]
	reason = filter_emojis_only(reason)

	if reason.startswith('!') and v.admin_level > 1:
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
		flag = Flag(post_id=post.id, user_id=v.id, reason=reason)
		g.db.add(flag)
		g.db.query(Submission) \
			.where(Submission.id == post.id, Submission.filter_state != 'ignored') \
			.update({Submission.filter_state: 'reported'})

	g.db.commit()

	return {"message": "Post reported!"}


@app.post("/report/comment/<cid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def api_flag_comment(cid, v):

	comment = get_comment(cid)
	reason = request.values.get("reason", "").strip()[:100]
	reason = filter_emojis_only(reason)

	flag = CommentFlag(comment_id=comment.id, user_id=v.id, reason=reason)
	g.db.add(flag)
	g.db.query(Comment) \
			.where(Comment.id == comment.id, Comment.filter_state != 'ignored') \
			.update({Comment.filter_state: 'reported'})
	g.db.commit()

	return {"message": "Comment reported!"}
