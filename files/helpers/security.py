from werkzeug.security import *

from files.helpers.config.environment import SECRET_KEY


def generate_hash(string):
	msg = bytes(string, "utf-16")

	return hmac.new(key=bytes(SECRET_KEY, "utf-16"),
					msg=msg,
					digestmod='md5'
					).hexdigest()


def validate_hash(string, hashstr):
	if not string or not hashstr: return False
	return hmac.compare_digest(hashstr, generate_hash(string))


def hash_password(password):
	return generate_password_hash(
		password, method='pbkdf2:sha512', salt_length=8)
