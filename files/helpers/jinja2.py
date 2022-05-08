from files.__main__ import app
from .get import *
from os import listdir, environ
from .const import * 
import time
from datetime import datetime

@app.template_filter("post_embed")
def post_embed(id, v):

	try: id = int(id)
	except: return None
	
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


@app.context_processor
def inject_constants():
	return {"environ":environ, "SITE":SITE, "SITE_NAME":SITE_NAME, "SITE_FULL":SITE_FULL, "AUTOJANNY_ID":AUTOJANNY_ID, "NOTIFICATIONS_ID":NOTIFICATIONS_ID, "PUSHER_ID":PUSHER_ID, "CC":CC, "CC_TITLE":CC_TITLE, "listdir":listdir, "MOOSE_ID":MOOSE_ID, "AEVANN_ID":AEVANN_ID, "PIZZASHILL_ID":PIZZASHILL_ID, "config":app.config.get, "DEFAULT_COLOR":DEFAULT_COLOR, "COLORS":COLORS, "ADMIGGERS":ADMIGGERS, "datetime":datetime}