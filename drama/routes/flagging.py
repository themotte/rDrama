from drama.helpers.wrappers import *
from drama.helpers.get import *
from flask import g
from drama.__main__ import app


@app.route("/api/flag/post/<pid>", methods=["POST"])
@auth_desired
def api_flag_post(pid, v):

	post = get_post(pid)

	if v:
		existing = g.db.query(Flag).filter_by(
			user_id=v.id, post_id=post.id).filter(
			Flag.created_utc >= post.edited_utc).first()

		if existing:
			return "", 409
		reason = request.form.get("reason", "")[:100].strip()
		flag = Flag(post_id=post.id,
					user_id=v.id,
					reason=reason,
					created_utc=int(time.time())
					)
					

		g.db.add(flag)

	return "", 204


@app.route("/api/flag/comment/<cid>", methods=["POST"])
@auth_desired
def api_flag_comment(cid, v):

	comment = get_comment(cid)
	
	if v:
		existing = g.db.query(CommentFlag).filter_by(
			user_id=v.id, comment_id=comment.id).filter(
			CommentFlag.created_utc >= comment.edited_utc).first()

		if existing:
			return "", 409

		reason = request.form.get("reason", "")[:100].strip()
		print(reason)
		flag = CommentFlag(comment_id=comment.id,
						   user_id=v.id,
						   reason=reason,
						   created_utc=int(time.time())
						   )

		g.db.add(flag)

	return "", 204