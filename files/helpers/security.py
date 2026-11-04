import time

from werkzeug.security import *

from files.helpers.config.environment import SECRET_KEY


def generate_hash(string):
	msg = bytes(string, "utf-16")
	return hmac.new(key=bytes(SECRET_KEY, "utf-16"),
					msg=msg,
					digestmod='md5'
					).hexdigest()


def validate_hash(string, hashstr):
	return hashstr.isascii() and hmac.compare_digest(hashstr, generate_hash(string))


def token_sign(purpose, *fields):
	'''The signature of `fields` for `purpose`. The purpose comes first in the signed message, so a signature issued for one purpose never passes for another.'''
	return generate_hash("+".join([purpose, *map(str, fields)]))


def token_verify(purpose, token, *fields):
	return bool(token) and validate_hash("+".join([purpose, *map(str, fields)]), token)


# How far ahead of this server's clock a token's time may be, for tokens issued by another server running the site.
TOKEN_CLOCK_SKEW = 60


def token_fresh(issued, lifetime):
	'''Whether a token stamped `issued` (epoch seconds) is still within `lifetime` seconds, and wasn't stamped in the future (beyond the clock skew allowed).'''
	return -TOKEN_CLOCK_SKEW <= int(time.time()) - issued <= lifetime

