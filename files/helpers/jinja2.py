import random
from os import environ, listdir

from jinja2 import pass_context

from files.__main__ import app
from files.helpers.assetcache import assetcache_path
from files.helpers.config.environment import (DEFAULT_COLOR, PUSHER_ID, SITE,
                                              SITE_FULL, SITE_ID, SITE_TITLE)
from files.helpers.time import format_age

from .config.const import *
from .get import *


@app.template_filter("computer_size")
def computer_size(size_bytes:int) -> str:
	return f'{size_bytes // 1024 // 1024} MiB'

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
	if not timestamp: return ''
	return format_age(timestamp)


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
		"COMMENT_BODY_LENGTH_MAXIMUM":COMMENT_BODY_LENGTH_MAXIMUM,
		"SUBMISSION_BODY_LENGTH_MAXIMUM":SUBMISSION_BODY_LENGTH_MAXIMUM,
		"DEFAULT_COLOR":DEFAULT_COLOR,
		"COLORS":COLORS,
		"THEMES":THEMES,
		"PERMS":PERMS,
		"FEATURES":FEATURES,
		"RENDER_DEPTH_LIMIT":RENDER_DEPTH_LIMIT,
		"SORTS_COMMENTS":SORTS_COMMENTS,
		"SORTS_POSTS":SORTS_POSTS,
		"CSS_LENGTH_MAXIMUM":CSS_LENGTH_MAXIMUM,
	}


def template_function(func):
	assert(func.__name__ not in app.jinja_env.globals)
	app.jinja_env.globals[func.__name__] = func
