'''
Arrange-phase factories: insert rows directly, so tests set up state cheaply and can reach states HTTP can't (old timestamps, bans, admin levels).

A factory user is a copy of a real account created through the signup form once per session, so every column the app sets at signup is right by construction.
'''
import hashlib
import html
import itertools
import secrets
import time

from files.tests.spec.harness import db
from files.tests.spec.harness.http import Client

PASSWORD = "correct horse battery staple"

_SALT = "spectest"
# Production hashes use far more; logins must accept any count, and few keep tests fast
FAST_HASH_ITERATIONS = 1000


def passhash_for(password: str, iterations: int) -> str:
	'''A stored password hash in werkzeug's "pbkdf2:sha512:<iterations>$salt$hex" format, as production uses.'''
	return f"pbkdf2:sha512:{iterations}${_SALT}${hashlib.pbkdf2_hmac('sha512', password.encode(), _SALT.encode(), iterations).hex()}"


PASSHASH = passhash_for(PASSWORD, FAST_HASH_ITERATIONS)

_counter = itertools.count(1)
_signup_template: dict | None = None

# Per-account columns that the factory sets itself rather than copying from the template
_IDENTITY_COLUMNS = {"id", "username", "original_username", "passhash", "created_utc", "admin_level"}


def unique(prefix="tok") -> str:
	'''A token that appears nowhere else, for asserting presence/absence in responses without false hits.'''
	return f"{prefix}{next(_counter)}x"


def has_signup_template() -> bool:
	return _signup_template is not None


def capture_signup_template():
	global _signup_template
	username = unique("signup")
	client = Client()
	form = client.get("/signup")
	r = client.post_raw("/signup", {
		"formkey": form.form_field("formkey"),
		"now": form.form_field("now"),
		"usernametwo": username,
		"email": "",
		"password": PASSWORD,
		"password_confirm": PASSWORD,
	})
	assert r.status == 302, f"signing up the template account failed with status {r.status}"
	row = db.row("users", username=username)
	server_generated = {c.name for c in db.table("users").columns if c.server_default is not None and "now()" in str(c.server_default.arg)}
	_signup_template = {k: v for k, v in row.items() if k not in _IDENTITY_COLUMNS | server_generated}


def user(**overrides) -> dict:
	username = overrides.pop("username", unique("user"))
	return db.insert("users", **{
		**_signup_template,
		"username": username,
		"original_username": username,
		"passhash": PASSHASH,
		"created_utc": int(time.time()),
		"admin_level": 0,
		**overrides,
	})


def admin(level: int, **overrides) -> dict:
	return user(admin_level=level, **overrides)



def post(author: dict, **overrides) -> dict:
	'''
	A post as submitting it creates one, with the author's own upvote and post count, but without the notifications publishing sends.

	`body` without `body_html` gets the body rendered as one plain paragraph; `title_html` likewise follows `title`.
	'''
	title = overrides.pop("title", unique("title"))
	body = overrides.get("body")
	row = db.insert("submissions", **{
		"author_id": author["id"],
		"created_utc": int(time.time()),
		"title": title,
		"title_html": html.escape(title),
		"body_html": f"<p>{html.escape(body)}</p>" if body else None,
		"state_mod": "VISIBLE",
		"state_report": "UNREPORTED",
		"upvotes": 1,
		"realupvotes": 1,
		**overrides,
	})
	db.insert("votes", user_id=author["id"], submission_id=row["id"], vote_type=1)
	db.execute("UPDATE users SET post_count = (SELECT count(*) FROM submissions WHERE author_id = :id AND state_mod = 'VISIBLE' AND state_user_deleted_utc IS NULL AND NOT private) WHERE id = :id", id=author["id"])
	return row


def comment(author: dict, post: dict, parent: dict | None = None, **overrides) -> dict:
	'''
	A comment on `post` (replying to `parent` if given) as commenting creates one: its own upvote, its place in the thread, and, when visible from an author who isn't shadowbanned, the comment counts of its ancestors, the post and the author. No notifications.
	'''
	body = overrides.pop("body", unique("comment"))
	comment_id = db.execute("SELECT nextval('comments_id_seq')")
	row = db.insert("comments", **{
		"id": comment_id,
		"author_id": author["id"],
		"created_utc": int(time.time()),
		"parent_submission": post["id"],
		"parent_comment_id": parent["id"] if parent else None,
		"level": parent["level"] + 1 if parent else 1,
		"top_comment_id": parent["top_comment_id"] if parent else comment_id,
		"over_18": post["over_18"],
		"ghost": post["ghost"],
		"body": body,
		"body_html": f"<p>{html.escape(body)}</p>",
		"volunteer_janitor_badness": 0.5,
		"state_mod": "VISIBLE",
		"state_report": "UNREPORTED",
		"upvotes": 1,
		**overrides,
	})
	db.insert("commentvotes", user_id=author["id"], comment_id=comment_id, vote_type=1)
	shadowbanned = db.execute("SELECT shadowbanned FROM users WHERE id = :id", id=author["id"])
	if row["state_mod"] == "VISIBLE" and row["state_user_deleted_utc"] is None and not shadowbanned:
		db.execute("UPDATE submissions SET comment_count = comment_count + 1 WHERE id = :id", id=post["id"])
		db.execute("UPDATE users SET comment_count = (SELECT count(*) FROM comments WHERE author_id = :id AND parent_submission IS NOT NULL AND state_mod = 'VISIBLE' AND state_user_deleted_utc IS NULL) WHERE id = :id", id=author["id"])
		db.execute("""
			WITH RECURSIVE ancestors(id, parent_comment_id) AS (
				SELECT id, parent_comment_id FROM comments WHERE id = :parent
				UNION ALL
				SELECT c.id, c.parent_comment_id FROM comments c JOIN ancestors a ON c.id = a.parent_comment_id
			)
			UPDATE comments SET descendant_count = descendant_count + 1 WHERE id IN (SELECT id FROM ancestors)
		""", parent=row["parent_comment_id"])
	return row


def api_token(user: dict) -> str:
	'''An access token for an approved API application owned by `user`, authenticating as `user`.'''
	application = db.insert("oauth_apps", client_id=secrets.token_urlsafe(48), app_name=unique("app"), redirect_uri="https://example.com/callback", author_id=user["id"], description=unique("description"))
	token = secrets.token_urlsafe(96)
	db.insert("client_auths", user_id=user["id"], oauth_client=application["id"], access_token=token)
	return token
