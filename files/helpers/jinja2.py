from files.__main__ import app
from .get import *


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
	
	p = get_post(id, graceful=True)
	
	return render_template("submission_listing.html", listing=[p], v=v)