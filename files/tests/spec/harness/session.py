'''
The session cookie and form key formats. Both are contract: old and new implementations must accept each other's cookies and form keys so they can serve the same users side by side.

Session cookie: named `session_<site id, lowercased>`; value is an itsdangerous URL-safe timed signature keyed by MASTER_KEY (HMAC key derivation, SHA-1, salt "cookie-session") over compact JSON, zlib-compressed with a leading "." whenever that is shorter. Payload values are restricted to JSON types (no tagged types). Keys:
- `_permanent`: true.
- `session_id`: 98 hex chars, assigned on first request and on login.
- `lo_user`, `login_nonce`: the logged-in user's id, and their `users.login_nonce` at login. The session is invalid once the stored nonce exceeds it.
- `history`: ids of accounts that have logged in from this browser (alt detection).
- `verified`: epoch seconds, set when the site owner logs in.
- `over_18`: epoch seconds until which the adult-content interstitial is waived.
- `signup_token`: hex, issued by the signup form and consumed by signup.
- `tooltip_last_dismissed`: epoch seconds.

Form key: lowercase hex HMAC-MD5 of "<session_id>+<user id>+<users.login_nonce>", with key (MASTER_KEY) and message both encoded UTF-16LE with a leading byte-order mark (FF FE). Accepted from the form body, the query string, or a `formkey` member of a JSON body.
'''
import hashlib
import hmac
import json
import secrets

import itsdangerous

from files.tests.spec.harness import config


class _CompactJson:
	@staticmethod
	def dumps(obj):
		return json.dumps(obj, separators=(",", ":"))

	@staticmethod
	def loads(s):
		return json.loads(s)


def cookie_name():
	return f"session_{config.site_id().lower()}"


def _serializer():
	return itsdangerous.URLSafeTimedSerializer(
		config.master_key(),
		salt="cookie-session",
		serializer=_CompactJson,
		signer_kwargs={"key_derivation": "hmac", "digest_method": hashlib.sha1},
	)


def encode(payload: dict) -> str:
	return _serializer().dumps(payload)


def decode(cookie_value: str) -> dict:
	return _serializer().loads(cookie_value)


def logged_in_payload(user_id: int, login_nonce: int) -> dict:
	return {"_permanent": True, "session_id": secrets.token_hex(49), "lo_user": user_id, "login_nonce": login_nonce}


def formkey(session_id: str, user_id: int, login_nonce: int) -> str:
	msg = f"{session_id}+{user_id}+{login_nonce}"
	bom = b"\xff\xfe"
	return hmac.new(key=bom + config.master_key().encode("utf-16-le"), msg=bom + msg.encode("utf-16-le"), digestmod="md5").hexdigest()
