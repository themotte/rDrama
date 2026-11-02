'''
Arrange-phase factories: insert rows directly, so tests set up state cheaply and can reach states HTTP can't (old timestamps, bans, admin levels).

A factory user is a copy of a real account created through the signup form once per session, so every column the app sets at signup is right by construction.
'''
import hashlib
import itertools
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

