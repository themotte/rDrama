from files.__main__ import app


@app.template_filter("full_link")
def full_link(url):

	return f"https://{app.config['SERVER_NAME']}{url}"


@app.template_filter("app_config")
def app_config(x):
	return app.config.get(x)