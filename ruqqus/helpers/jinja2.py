from os import environ, path
import calendar
from .get import *
from ruqqus.__main__ import app, cache


@app.template_filter("total_users")
@cache.memoize(timeout=60)
def total_users(x):

	return db.query(User).filter_by(is_banned=0).count()


@app.template_filter("source_code")
@cache.memoize(timeout=60 * 60 * 24)
def source_code(file_name):

	return open(path.expanduser('~') + '/ruqqus/' +
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


@app.template_filter("is_mod")
@cache.memoize(60)
def jinja_is_mod(uid, bid):

	return bool(get_mod(uid, bid))

@app.template_filter("coin_goal")
@cache.cached(timeout=600, key_prefix="premium_coin_goal")
def coin_goal(x):
	
	now = time.gmtime()
	midnight_month_start = time.struct_time((now.tm_year,
											  now.tm_mon,
											  1,
											  0,
											  0,
											  0,
											  now.tm_wday,
											  now.tm_yday,
											  0)
											 )
	cutoff = calendar.timegm(midnight_month_start)
	
	coins=g.db.query(func.sum(PayPalTxn.coin_count)).filter(
		PayPalTxn.created_utc>cutoff,
		PayPalTxn.status==3).all()[0][0] or 0
	
	
	return int(100*coins/1000)


@app.template_filter("app_config")
def app_config(x):
	return app.config.get(x)

# @app.template_filter("general_chat_count")
# def general_chat_count(x):
#	 return get_guild("general").chat_count	