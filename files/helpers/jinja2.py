from files.__main__ import app
from .get import *
from os import listdir, environ
from .const import * 

@app.template_filter("full_link")
def full_link(url):

	return f"https://{app.config['SERVER_NAME']}{url}"

@app.template_filter("app_config")
def app_config(x):
	return app.config.get(x)

@app.template_filter("post_embed")
def post_embed(id, v):

	try: id = int(id)
	except: return None
	
	p = get_post(id, v, graceful=True)
	
	if not v or v.oldsite: template = ''
	else: template = 'CHRISTMAS/'
	return render_template(f"{template}submission_listing.html", listing=[p], v=v)

@app.context_processor
def inject_constants():
	return {"num_banners":num_banners, "environ":environ, "SITE_NAME":SITE_NAME, "AUTOJANNY_ID": AUTOJANNY_ID, "NOTIFICATIONS_ID": NOTIFICATIONS_ID}