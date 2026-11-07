from typing import Optional

from files.classes import *
from flask import g

from .sanitize import *
from files.helpers.get import get_user
from .config.const import *
from files.classes.visstate import StateMod

def create_comment(text_html, autojanny=False):
	if autojanny: author_id = AUTOJANNY_ID
	else: author_id = NOTIFICATIONS_ID

	new_comment = Comment(author_id=author_id,
							parent_submission=None,
							body_html=text_html,
							distinguish_level=6,
							state_mod=StateMod.VISIBLE,)
	g.db.add(new_comment)
	g.db.flush()

	new_comment.top_comment_id = new_comment.id

	return new_comment.id

def send_repeatable_notification(uid, text, autojanny=False):
	if autojanny: author_id = AUTOJANNY_ID
	else: author_id = NOTIFICATIONS_ID
	
	text_html = sanitize(text)

	existing_comment = g.db.query(Comment.id).filter_by(author_id=author_id, parent_submission=None, body_html=text_html).first()

	if existing_comment:
		cid = existing_comment[0]
		existing_notif = g.db.query(Notification.user_id).filter_by(user_id=uid, comment_id=cid).one_or_none()
		if existing_notif: cid = create_comment(text_html, autojanny)
	else: cid = create_comment(text_html, autojanny)

	notif = Notification(comment_id=cid, user_id=uid)
	g.db.add(notif)


def send_notification(uid, text, autojanny=False):
	cid = notif_comment(text, autojanny)
	add_notif(cid, uid)


def notif_comment(text, autojanny=False):
	if autojanny:
		author_id = AUTOJANNY_ID
		alert = True
	else:
		author_id = NOTIFICATIONS_ID
		alert = False

	text_html = sanitize(text, alert=alert)

	existing = g.db.query(Comment.id).filter_by(author_id=author_id, parent_submission=None, body_html=text_html).one_or_none()
	
	if existing: return existing[0]
	else: return create_comment(text_html, autojanny)


def notif_comment2(p):
	search_html = f'%</a> has mentioned you: <a href="/post/{p.id}">%'

	existing = g.db.query(Comment.id).filter(Comment.author_id == NOTIFICATIONS_ID, Comment.parent_submission == None, Comment.body_html.like(search_html)).first()
	
	if existing: return existing[0]
	else:
		text = f"@{p.author.username} has mentioned you: [{p.title}](/post/{p.id})"
		text_html = sanitize(text, alert=True)
		return create_comment(text_html)


def add_notif(cid, uid):
	existing = g.db.query(Notification.user_id).filter_by(comment_id=cid, user_id=uid).one_or_none()
	if not existing:
		notif = Notification(comment_id=cid, user_id=uid)
		g.db.add(notif)


def notify_modmail(comment_id: int, besides: Optional[User]) -> set[int]:
	'''Notifies the admins who receive modmail of the modmail comment `comment_id`, except `besides` (its writer, when an admin), and returns their ids.'''
	admins = g.db.query(User.id).filter(User.admin_level > 2)
	if besides: admins = admins.filter(User.id != besides.id)
	notified = {admin_id for (admin_id,) in admins}
	for admin_id in notified:
		g.db.add(Notification(comment_id=comment_id, user_id=admin_id))
	return notified


def NOTIFY_USERS(text, v) -> set[int]:
	notify_users = set()

	captured = []
	for i in mention_regex.finditer(text):
		if v.username.lower() == i.group(2).lower(): continue

		if i.group(0) in captured: continue
		captured.append(i.group(0))

		user = get_user(i.group(2), graceful=True)
		if user and v.id != user.id and not v.any_block_exists(user): 
			notify_users.add(user.id)

	return notify_users

def notify_submission_publish(target: Submission):
	# Username mentions in title & body
	text: str = f'{target.title} {target.body}'
	notify_users = NOTIFY_USERS(text, target.author)
	if notify_users:
		comment_id = notif_comment2(target)
		for user_id in notify_users:
			add_notif(comment_id, user_id)

	# Submission author followers
	follower_ids = [uid for (uid,) in g.db.query(Follow.user_id).filter(
		Follow.target_id == target.author_id).all()]
	if follower_ids:
		message: str = (
			f"@{target.author.username} has made a new post: "
			f"[{target.title}]({target.shortlink})"
		)
		cid = notif_comment(message, autojanny=True)
		for user_id in follower_ids:
			add_notif(cid, user_id)
