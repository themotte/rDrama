import mistletoe

from files.classes import *
from flask import g
from .markdown import *
from .sanitize import *
from .const import *

def create_comment(text, autojanny=False):
	if autojanny: author_id = AUTOJANNY_ID
	else: author_id = NOTIFICATIONS_ID

	text_html = sanitize(Renderer2().render(mistletoe.Document(text)))

	for i in re.finditer("^@((\w|-){1,25})", text_html):
		text_html = text_html.replace(i.group(1), f'<a href="/@{i.group(1)}"><img loading="lazy" src="/@{i.group(1)}/pic" class="pp20">@{i.group(1)}</a>')

	new_comment = Comment(author_id=author_id,
							parent_submission=None,
							distinguish_level=6,
							body=text,
							created_utc=0,
							body_html=text_html)
	g.db.add(new_comment)
	g.db.flush()
	return new_comment.id

def send_repeatable_notification(uid, text, autojanny=False):

	if autojanny: author_id = AUTOJANNY_ID
	else: author_id = NOTIFICATIONS_ID
	
	existing_comment = g.db.query(Comment.id).filter_by(author_id=author_id, parent_submission=None, distinguish_level=6, body=text, created_utc=0).first()

	if existing_comment:
		cid = existing_comment[0]
		existing_notif = g.db.query(Notification.id).filter_by(user_id=uid, comment_id=cid).first()
		if existing_notif: cid = create_comment(text, autojanny)
	else: cid = create_comment(text, autojanny)

	notif = Notification(comment_id=cid, user_id=uid)
	g.db.add(notif)


def send_notification(uid, text, autojanny=False):

	cid = notif_comment(text, autojanny)
	add_notif(cid, uid)


def notif_comment(text, autojanny=False):

	if autojanny: author_id = AUTOJANNY_ID
	else: author_id = NOTIFICATIONS_ID

	existing = g.db.query(Comment.id).filter_by(author_id=author_id, parent_submission=None, distinguish_level=6, body=text, created_utc=0).first()
	
	if existing: return existing[0]
	else: return create_comment(text, autojanny)


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


def NOTIFY_USERS(text, v):
	notify_users = set()
	for word, id in NOTIFIED_USERS.items():
		if id == 0: continue
		if word in text.lower() and id not in notify_users and v.id != id: notify_users.add(id)

	soup = BeautifulSoup(text, features="html.parser")
	for mention in soup.find_all("a", href=re.compile("^/@(\w+)")):
		username = mention["href"].split("@")[1]
		user = g.db.query(User).filter_by(username=username).first()
		if user and not v.any_block_exists(user) and user.id != v.id: notify_users.add(user.id)

	return notify_users