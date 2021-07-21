import html
from .front import frontlist
from datetime import datetime
from ruqqus.helpers.jinja2 import full_link
from ruqqus.helpers.get import *
from yattag import Doc

from ruqqus.__main__ import app

@app.route('/rss/<sort>/<t>', methods=["GET"])
def feeds_user(sort='hot', t='all'):

	page = int(request.args.get("page", 1))

	posts = frontlist(
		sort=sort,
		page=page,
		t=t,
		v=None,
		hide_offensive=False,
		ids_only=False)

	domain = environ.get(
	"domain", environ.get(
		"SERVER_NAME", None)).strip()

	doc, tag, text = Doc().tagtext()

	with tag("feed", ("xmlns:media","http://search.yahoo.com/mrss/"), xmlns="http://www.w3.org/2005/Atom",):
		with tag("title", type="text"):
			text(f"{sort} posts from {domain}")

		doc.stag("link", href=request.url)
		doc.stag("link", href=request.url_root)

		for post in posts:
			#print("POST IMAGE "+ str( post.is_image ))
			board_name = f"+{post.board.name}"
			with tag("entry", ("xml:base", request.url)):
				with tag("title", type="text"):
					text(post.title)

				with tag("id"):
					text(post.fullname)

				if (post.edited_utc > 0):
					with tag("updated"):
						text(datetime.utcfromtimestamp(post.edited_utc).isoformat())

				with tag("published"):
					text(datetime.utcfromtimestamp(post.created_utc).isoformat())
				
				doc.stag("link", href=post.url)

				with tag("author"):
					with tag("name"):
						text(post.author.username)
					with tag("uri"):
						text(f'https://{domain}/@{post.author.username}')

				doc.stag("link", href=full_link(post.permalink))

				doc.stag("category", term=board_name, label=board_name, schema=full_link("/" + board_name))

				image_url = post.thumb_url or post.embed_url or post.url

				doc.stag("media:thumbnail", url=image_url)

				if len(post.body_html) > 0:
					with tag("content", type="html"):
						text(html.escape(f"<img src={image_url}/><br/>{post.body_html}"))

	return Response( "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"+ doc.getvalue(), mimetype="application/xml")