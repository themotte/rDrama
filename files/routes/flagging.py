from files.helpers.wrappers import *
from files.helpers.get import *
from flask import g
from files.__main__ import app
from files.helpers.sanitize import sanitize

@app.post("/flag/post/<pid>")
@auth_desired
def api_flag_post(pid, v):

	post = get_post(pid)

	if v:
		existing = g.db.query(Flag).filter_by(user_id=v.id, post_id=post.id).first()

		if existing: return "", 409
		reason = sanitize(request.form.get("reason", "").strip()[:100], flair=True)

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

		if existing: return "", 409
		reason = sanitize(request.form.get("reason", "")[:100].strip(), flair=True)
		flag = CommentFlag(comment_id=comment.id,
						   user_id=v.id,
						   reason=reason,
						   )

		g.db.add(flag)

	return "", 204