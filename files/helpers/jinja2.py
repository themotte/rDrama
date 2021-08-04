from os import environ, path
from .get import *
from files.__main__ import app, cache


@app.template_filter("total_users")
@cache.memoize(timeout=60)
def total_users(x):

	return db.query(User).filter_by(is_banned=0).count()


@app.template_filter("source_code")
@cache.memoize(timeout=60 * 60 * 24)
def source_code(file_name):

	return open(path.expanduser('~') + '/files/' +
				file_name, mode="r+").read()


@app.template_filter("full_link")
def full_link(url):

	return f"https://{app.config['SERVER_NAME']}{url}"


@app.template_filter("env")
def env_var_filter(x):

	x = environ.get(x, 1)

	try:
		return int(x)
	except BaseException:
		try:
			return float(x)
		except BaseException:
			return x


@app.template_filter("js_str_escape")
def js_str_escape(s):

	s = s.replace("'", r"\'")

	return s


@app.template_filter("app_config")
def app_config(x):
	return app.config.get(x)