from os import listdir, environ
import random
import time

from jinja2 import pass_context

from files.__main__ import app
from .get import *
from .const import * 
from files.helpers.assetcache import assetcache_path


@app.template_filter("shuffle")
@pass_context
def template_shuffle(ctx, l: list) -> list:
	# Uses @pass_context while ignoring `ctx` to prevent Jinja from
	# caching the result of the filter

	# stdlib recommended idiom for shuffling out-of-place
	# as opposed to random.shuffle for in-place shuffling
	return random.sample(l, k=len(l))


@app.template_filter("post_embed")
def post_embed(id, v):
	p = get_post(id, v, graceful=True)
	
	if p: return render_template("submission_listing.html", listing=[p], v=v)
	return ''


@app.template_filter("timestamp")
def timestamp(timestamp):

	age = int(time.time()) - timestamp

	if age < 60:
		return "just now"
	elif age < 3600:
		minutes = int(age / 60)
		return f"{minutes}m ago"
	elif age < 86400:
		hours = int(age / 3600)
		return f"{hours}hr ago"
	elif age < 2678400:
		days = int(age / 86400)
		return f"{days}d ago"

	now = time.gmtime()
	ctd = time.gmtime(timestamp)

	months = now.tm_mon - ctd.tm_mon + 12 * (now.tm_year - ctd.tm_year)
	if now.tm_mday < ctd.tm_mday:
		months -= 1

	if months < 12:
		return f"{months}mo ago"
	else:
		years = int(months / 12)
		return f"{years}yr ago"


@app.template_filter("asset")
def template_asset(asset_path):
	return assetcache_path(asset_path)


@app.context_processor
def inject_constants():
	return {
		"environ":environ,
		"SITE":SITE,
		"SITE_ID":SITE_ID,
		"SITE_TITLE":SITE_TITLE,
		"SITE_FULL":SITE_FULL,
		"AUTOJANNY_ID":AUTOJANNY_ID,
		"NOTIFICATIONS_ID":NOTIFICATIONS_ID,
		"MODMAIL_ID":MODMAIL_ID,
		"PUSHER_ID":PUSHER_ID,
		"CC":CC,
		"CC_TITLE":CC_TITLE,
		"listdir":listdir,
		"config":app.config.get,
		"DEFAULT_COLOR":DEFAULT_COLOR,
		"COLORS":COLORS,
		"THEMES":THEMES,
		"PERMS":PERMS,
		"FEATURES":FEATURES,
		"RENDER_DEPTH_LIMIT":RENDER_DEPTH_LIMIT,
	}


def template_function(func):
	assert(func.__name__ not in app.jinja_env.globals)
	app.jinja_env.globals[func.__name__] = func
