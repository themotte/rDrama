from files.helpers.wrappers import *
from files.helpers.get import *
from flask import g
from files.__main__ import app
from files.helpers.sanitize import sanitize
from os import path

@app.post("/flag/post/<pid>")
@auth_desired
def api_flag_post(pid, v):

	post = get_post(pid)

	if v:
		existing = g.db.query(Flag).filter_by(user_id=v.id, post_id=post.id).first()

		if existing: return "", 409

		reason = request.form.get("reason", "").strip()[:100]

		for i in re.finditer(':(.{1,30}?):', reason):
			if path.isfile(f'./files/assets/images/emojis/{i.group(1)}.gif'):
				reason = reason.replace(f':{i.group(1)}:', f'<img data-toggle="tooltip" title="{i.group(1)}" delay="0" height=20 src="https://{site}/assets/images/emojis/{i.group(1)}.gif"<span>')

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
		reason = request.form.get("reason", "").strip()[:100]

		for i in re.finditer(':(.{1,30}?):', reason):
			if path.isfile(f'./files/assets/images/emojis/{i.group(1)}.gif'):
				reason = reason.replace(f':{i.group(1)}:', f'<img data-toggle="tooltip" title="{i.group(1)}" delay="0" height=20 src="https://{site}/assets/images/emojis/{i.group(1)}.gif"<span>')

		flag = CommentFlag(comment_id=comment.id,
					user_id=v.id,
					reason=reason,
					)

		g.db.add(flag)

	return "", 204