import mistletoe

from files.classes import *
from flask import g
from .markdown import *
from .sanitize import *
from .const import *

def send_repeatable_notification(uid, text, autojanny=False):

	text = text.replace('r/', 'r\/').replace('u/', 'u\/')

	if autojanny: author_id = AUTOJANNY_ID
	else: author_id = NOTIFICATIONS_ID
	
	existing = g.db.query(Comment.id).filter_by(author_id=author_id, parent_submission=None, distinguish_level=6, body=text, created_utc=0).first()
	if existing:
		existing2 = g.db.query(Notification.id).filter_by(user_id=uid, comment_id=existing[0]).first()
		if existing2:
			text_html = sanitize(CustomRenderer().render(mistletoe.Document(text)))
			new_comment = Comment(author_id=author_id,
									parent_submission=None,
									distinguish_level=6,
									body=text,
									body_html=text_html,
									created_utc=0)
			g.db.add(new_comment)
			g.db.flush()
			notif = Notification(comment_id=new_comment.id, user_id=uid)
			g.db.add(notif)
			return

	send_notification(uid, text, autojanny)


def send_notification(uid, text, autojanny=False):

	cid = notif_comment(text, autojanny)
	add_notif(cid, uid)


def notif_comment(text, autojanny=False):

	text = text.replace('r/', 'r\/').replace('u/', 'u\/')

	if autojanny: author_id = AUTOJANNY_ID
	else: author_id = NOTIFICATIONS_ID
	
	existing = g.db.query(Comment.id).filter_by(author_id=author_id, parent_submission=None, distinguish_level=6, body=text, created_utc=0).first()
	
	if existing: cid = existing[0]
	else:
		text_html = sanitize(CustomRenderer().render(mistletoe.Document(text)))
		new_comment = Comment(author_id=author_id,
								parent_submission=None,
								distinguish_level=6,
								body=text,
								body_html=text_html,
								created_utc=0)
		g.db.add(new_comment)
		g.db.flush()
		cid = new_comment.id

	return cid

def add_notif(cid, uid):
	existing = g.db.query(Notification.id).filter_by(comment_id=cid, user_id=uid).first()
	if not existing:
		notif = Notification(comment_id=cid, user_id=uid)
		g.db.add(notif)

def send_admin(vid, text):

	text_html = Renderer().render(mistletoe.Document(text))

	text_html = sanitize(text_html, True)

	new_comment = Comment(author_id=vid,
						  parent_submission=None,
						  level=1,
						  sentto=0,
						  body_html=text_html,
						  )
	g.db.add(new_comment)
	g.db.flush()

	admins = g.db.query(User).filter(User.admin_level > 0).all()
	for admin in admins:
		notif = Notification(comment_id=new_comment.id, user_id=admin.id)
		g.db.add(notif)

def NOTIFY_USERS(text, vid):
	text = text.lower()
	notify_users = set()
	for word, id in NOTIFIED_USERS.items():
		if id == 0: continue
		if word in text and id not in notify_users and vid != id: notify_users.add(id)
	return notify_users