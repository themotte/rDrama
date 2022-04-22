from files.helpers.wrappers import *
from files.helpers.get import *
from flask import g
from files.__main__ import app, limiter
from os import path
from files.helpers.sanitize import filter_emojis_only

@app.post("/report/post/<pid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def api_flag_post(pid, v):

	post = get_post(pid)

	reason = request.values.get("reason", "").strip()

	if blackjack and any(i in reason.lower() for i in blackjack.split()):
		v.shadowbanned = 'AutoJanny'
		send_repeatable_notification(CARP_ID, f"reports on {post.permalink}")

	reason = reason[:100]

	if not reason.startswith('!'):
		existing = g.db.query(Flag.post_id).filter_by(user_id=v.id, post_id=post.id).one_or_none()
		if existing: return "", 409

	reason = filter_emojis_only(reason)

	if len(reason) > 350: return {"error": "Too long."}

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
	elif reason.startswith('/h/') and v.admin_level > 2:
		post.sub = reason[3:]
		g.db.add(post)
		ma=ModAction(
			kind="move_hole",
			user_id=v.id,
			target_submission_id=post.id,
		)
		g.db.add(ma)
	else:
		flag = Flag(post_id=post.id, user_id=v.id, reason=reason)
		g.db.add(flag)

	g.db.commit()

	return {"message": "Post reported!"}


@app.post("/report/comment/<cid>")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def api_flag_comment(cid, v):

	comment = get_comment(cid)
	
	existing = g.db.query(CommentFlag.comment_id).filter_by( user_id=v.id, comment_id=comment.id).one_or_none()
	if existing: return "", 409

	reason = request.values.get("reason", "").strip()

	if blackjack and any(i in reason.lower() for i in blackjack.split()):
		v.shadowbanned = 'AutoJanny'
		send_repeatable_notification(CARP_ID, f"reports on {comment.permalink}")

	reason = reason[:100]

	reason = filter_emojis_only(reason)

	if len(reason) > 350: return {"error": "Too long."}

	flag = CommentFlag(comment_id=comment.id, user_id=v.id, reason=reason)

	g.db.add(flag)
	g.db.commit()

	return {"message": "Comment reported!"}


@app.post('/del_report/post/<pid>/<uid>')
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@admin_level_required(2)
def remove_report_post(v, pid, uid):

	try:
		pid = int(pid)
		uid = int(uid)
	except: abort(400)

	report = g.db.query(Flag).filter_by(post_id=pid, user_id=uid).one()
	
	g.db.delete(report)

	ma=ModAction(
		kind="delete_report",
		user_id=v.id,
		target_submission_id=pid
	)

	g.db.add(ma)

	g.db.commit()

	return {"message": "Report removed successfully!"}


@app.post('/del_report/comment/<cid>/<uid>')
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@admin_level_required(2)
def remove_report_comment(v, cid, uid):
	
	cid = int(cid)
	uid = int(uid)
	
	report = g.db.query(CommentFlag).filter_by(comment_id=cid, user_id=uid).one()
	
	g.db.delete(report)

	ma=ModAction(
		kind="delete_report",
		user_id=v.id,
		target_comment_id=cid
	)

	g.db.add(ma)

	g.db.commit()

	return {"message": "Report removed successfully!"}