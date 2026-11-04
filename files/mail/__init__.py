import time
from urllib.parse import quote

from flask_mail import Message

from files.__main__ import app, limiter, mail
from files.classes.badges import Badge
from files.classes.user import User
from files.helpers.config.const import *
from files.helpers.config.environment import SITE_ID, SITE_TITLE
from files.helpers.security import *
from files.helpers.wrappers import *
from files.routes.importstar import *


def send_mail(to_address, subject, html):
	msg = Message(html=html, subject=subject, sender=f"{SITE_ID}@{SITE}", recipients=[to_address])
	mail.send(msg)


def activation_link(user, email):
	now = int(time.time())
	return f"{SITE_FULL}/activate?email={quote(email)}&id={user.id}&time={now}&token={token_sign('activate', email, user.id, now)}"


def send_verification_email(user):
	email = user.email
	link = activation_link(user, email)

	send_mail(to_address=email,
			  html=render_template("email/email_verify.html",
								   action_url=link,
								   v=user),
			  subject=f"Validate your {SITE_TITLE} account email."
			  )


@app.post("/verify_email")
@limiter.limit("1/second;30/minute;200/hour;1000/day")
@auth_required
def api_verify_email(v):
	if not v.email: abort(400, "Your account has no email address to verify.")
	send_verification_email(v)
	return {"message": "Email has been sent (ETA ~5 minutes)"}


@app.get("/activate")
@auth_required
def activate(v):
	email = request.values.get("email", "").strip().lower()

	if not email_regex.fullmatch(email):
		return render_template("message.html", v=v, title="Invalid email.", error="Invalid email."), 400


	id = request.values.get("id", "").strip()
	timestamp = request.values.get("time", type=int)
	if timestamp is None: abort(400)
	token = request.values.get("token", "").strip()

	if not token_fresh(timestamp, 3600):
		return render_template("message.html", v=v, title="Verification link expired.",
							   message="That link has expired. Visit your settings to send yourself another verification email."), 410

	if not token_verify('activate', token, email, id, timestamp):
		abort(403)

	if id != str(v.id):
		abort(403, "That verification link is for a different account.")

	if v.is_activated and v.email == email:
		return render_template("message_success.html", v=v, title="Email already verified.", message="Email already verified.")

	v.email = email
	v.is_activated = True

	if not any(b.badge_id == 2 for b in v.badges):
		mail_badge = Badge(user_id=v.id, badge_id=2)
		g.db.add(mail_badge)
		g.db.flush()
		send_notification(v.id, f"@AutoJanny has given you the following profile badge:\n\n![]({mail_badge.path})\n\n{mail_badge.name}")


	g.db.add(v)
	g.db.commit()

	return render_template("message_success.html", v=v, title="Email verified.", message=f"Your email {email} has been verified. Thank you.")
