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
	A post as submitting it creates one, with the author's own upvote (counted unless they're shadowbanned) and post count, but without the notifications publishing sends.

	`body` without `body_html` gets the body rendered as one plain paragraph; `title_html` likewise follows `title`.
	'''
	title = overrides.pop("title", unique("title"))
	body = overrides.get("body")
	counted = not db.execute("SELECT shadowbanned FROM users WHERE id = :id", id=author["id"])
	row = db.insert("submissions", **{
		"author_id": author["id"],
		"created_utc": int(time.time()),
		"title": title,
		"title_html": html.escape(title),
		"body_html": f"<p>{html.escape(body)}</p>" if body else None,
		"state_mod": "VISIBLE",
		"state_report": "UNREPORTED",
		"upvotes": int(counted),
		"realupvotes": int(counted),
		**overrides,
	})
	db.insert("votes", user_id=author["id"], submission_id=row["id"], vote_type=1, real=counted)
	db.execute("UPDATE users SET post_count = (SELECT count(*) FROM submissions WHERE author_id = :id AND state_mod = 'VISIBLE' AND state_user_deleted_utc IS NULL AND NOT private) WHERE id = :id", id=author["id"])
	return row


def comment(author: dict, post: dict, parent: dict | None = None, **overrides) -> dict:
	'''
	A comment on `post` (replying to `parent` if given) as commenting creates one: its own upvote (counted unless the author is shadowbanned), its place in the thread, its author's comment count, and, when visible from an author who isn't shadowbanned, the comment counts of its ancestors and the post. No notifications.
	'''
	body = overrides.pop("body", unique("comment"))
	shadowbanned = db.execute("SELECT shadowbanned FROM users WHERE id = :id", id=author["id"])
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
		"upvotes": 0 if shadowbanned else 1,
		"realupvotes": 0 if shadowbanned else 1,
		**overrides,
	})
	db.insert("commentvotes", user_id=author["id"], comment_id=comment_id, vote_type=1, real=not shadowbanned)
	db.execute("UPDATE users SET comment_count = (SELECT count(*) FROM comments c JOIN submissions s ON s.id = c.parent_submission WHERE c.author_id = :id AND c.state_mod = 'VISIBLE' AND c.state_user_deleted_utc IS NULL AND NOT s.private) WHERE id = :id", id=author["id"])
	if row["state_mod"] == "VISIBLE" and row["state_user_deleted_utc"] is None and not shadowbanned:
		db.execute("UPDATE submissions SET comment_count = comment_count + 1 WHERE id = :id", id=post["id"])
		db.execute("""
			WITH RECURSIVE ancestors(id, parent_comment_id) AS (
				SELECT id, parent_comment_id FROM comments WHERE id = :parent
				UNION ALL
				SELECT c.id, c.parent_comment_id FROM comments c JOIN ancestors a ON c.id = a.parent_comment_id
			)
			UPDATE comments SET descendant_count = descendant_count + 1 WHERE id IN (SELECT id FROM ancestors)
		""", parent=row["parent_comment_id"])
	return row


def message(author: dict, recipient: dict | int, parent: dict | None = None, **overrides) -> dict:
	'''
	A private message from `author` to `recipient` (a user, or an account id such as `seed.MODMAIL_ID`), replying to the message `parent` if given, as sending one leaves it: its place in the thread and its rendered text, but no stored source text, no vote and no notification.

	The returned row also carries "text", the sentinel its rendered text holds (`text=` chooses it).
	'''
	text = overrides.pop("text", unique("message"))
	message_id = db.execute("SELECT nextval('comments_id_seq')")
	row = db.insert("comments", **{
		"id": message_id,
		"author_id": author["id"],
		"sentto": recipient if isinstance(recipient, int) else recipient["id"],
		"created_utc": int(time.time()),
		"parent_submission": None,
		"parent_comment_id": parent["id"] if parent else None,
		"level": parent["level"] + 1 if parent else 1,
		"top_comment_id": parent["top_comment_id"] if parent else message_id,
		"body": None,
		"body_html": f"<p>{html.escape(text)}</p>",
		"volunteer_janitor_badness": 0.5,
		"state_mod": "VISIBLE",
		"state_report": "UNREPORTED",
		**overrides,
	})
	return {**row, "text": text}


def notification(user: dict, comment: dict, read: bool = False) -> dict:
	'''A notification for `user` of `comment` (a comment or message from these factories).'''
	return db.insert("notifications", user_id=user["id"], comment_id=comment["id"], read=read)


def vote(voter: dict, target: dict, vote_type: int) -> dict:
	'''
	`voter` votes `vote_type` (1, 0 or -1) on `target` (a post or a comment from these factories), as voting does: their vote row is set, the target's vote counts are recounted, and the author's truescore moves by the change unless the voter is the author. A shadowbanned voter's vote moves no counts.
	'''
	if "title" in target:
		table, votes, key = "submissions", "votes", "submission_id"
	else:
		table, votes, key = "comments", "commentvotes", "comment_id"
	real = not db.row("users", id=voter["id"])["shadowbanned"]
	old = db.execute(f"SELECT vote_type FROM {votes} WHERE user_id = :user AND {key} = :target", user=voter["id"], target=target["id"])
	if old == vote_type: return db.row(table, id=target["id"])
	if old is None:
		db.insert(votes, user_id=voter["id"], vote_type=vote_type, real=real, **{key: target["id"]})
	else:
		db.execute(f"UPDATE {votes} SET vote_type = :type, real = :real WHERE user_id = :user AND {key} = :target", type=vote_type, real=real, user=voter["id"], target=target["id"])
	author_id = db.execute(f"SELECT author_id FROM {table} WHERE id = :id", id=target["id"])
	if author_id != voter["id"] and real:
		db.execute("UPDATE users SET truescore = truescore + :delta WHERE id = :id", delta=vote_type - (old or 0), id=author_id)
	counted = "AND user_id IN (SELECT id FROM users WHERE shadowbanned IS NULL)"
	db.execute(f"""
		UPDATE {table} SET
			upvotes = (SELECT count(*) FROM {votes} WHERE {key} = :id AND vote_type = 1 {counted}),
			downvotes = (SELECT count(*) FROM {votes} WHERE {key} = :id AND vote_type = -1 {counted}),
			realupvotes = (SELECT count(*) FROM {votes} WHERE {key} = :id AND vote_type = 1 AND real)
		WHERE id = :id
	""", id=target["id"])
	return db.row(table, id=target["id"])


def api_token(user: dict) -> str:
	'''An access token for an approved API application owned by `user`, authenticating as `user`.'''
	application = db.insert("oauth_apps", client_id=secrets.token_urlsafe(48), app_name=unique("app"), redirect_uri="https://example.com/callback", author_id=user["id"], description=unique("description"))
	token = secrets.token_urlsafe(96)
	db.insert("client_auths", user_id=user["id"], oauth_client=application["id"], access_token=token)
	return token
