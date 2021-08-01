from drama.helpers.wrappers import *
from drama.helpers.get import *
from flask import g
from drama.__main__ import app


@app.post("/flag/post/<pid>")
@auth_desired
def api_flag_post(pid, v):

	post = get_post(pid)

	if v:
		existing = g.db.query(Flag).filter_by(
			user_id=v.id, post_id=post.id).first()

		if existing:
			return "", 409
		reason = request.form.get("reason", "")[:100].strip()
		flag = Flag(post_id=post.id,
					user_id=v.id,
					reason=reason,
					)
					

		g.db.add(flag)

	return "", 204


@app.post("/flag/comment/<cid>")
@auth_desired
def api_flag_comment(cid, v):

	comment = get_comment(cid)
	
	if v:
		existing = g.db.query(CommentFlag).filter_by(
			user_id=v.id, comment_id=comment.id).first()

		if existing:
			return "", 409

		reason = request.form.get("reason", "")[:100].strip()
		flag = CommentFlag(comment_id=comment.id,
						   user_id=v.id,
						   reason=reason,
						   )

		g.db.add(flag)

	return "", 204