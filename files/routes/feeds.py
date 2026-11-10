import time

from yattag import Doc

import files.helpers.listing as listing
from files.__main__ import app
from files.helpers.config.const import *
from files.helpers.get import *
from files.helpers.jinja2 import *
from files.helpers.wrappers import *


def _atom_time(epoch: float) -> str:
	'''`epoch` as an RFC 3339 time in UTC, as Atom wants it.'''
	return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


@app.get('/rss')
@app.get('/feed')
@app.get('/rss/<sort>/<t>')
def feeds_front(sort='new', t='all'):
	page = listing.request_page()

	ids, next_exists = listing.frontlist(
		sort=sort,
		page=page,
		t=t,
		v=None,
		)
	posts = get_posts(ids)

	doc, tag, text = Doc().tagtext()
	with tag("feed", ("xmlns:media","http://search.yahoo.com/mrss/"), xmlns="http://www.w3.org/2005/Atom",):
		with tag("title", type="text"):
			text(f"{sort} posts from {SITE_TITLE}")

		with tag("id"):
			text(SITE_FULL + request.full_path)
		with tag("updated"):
			text(_atom_time(time.time()))
		doc.stag("link", rel="self", type="application/atom+xml", href=SITE_FULL + request.full_path)
		doc.stag("link", rel="alternate", type="text/html", href=SITE_FULL)

		for post in posts:
			with tag("entry", ("xml:base", SITE_FULL + request.full_path)):
				with tag("title", type="html"):
					text(post.realtitle(None))

				with tag("id"):
					text(post.permalink)

				with tag("updated"):
					text(_atom_time(post.edited_utc or post.created_utc))

				with tag("published"):
					text(_atom_time(post.created_utc))
				
				with tag("author"):
					with tag("name"):
						text(post.author_name)
					with tag("uri"):
						text(f'/@{post.author_name}')

				doc.stag("link", href=post.permalink)

				image_url = post.thumb_url

				doc.stag("media:thumbnail", url=image_url)

				if post.body_html and not post.over_18:
					with tag("content", type="html"):
						doc.cdata(f'''<img alt="{post.realtitle(None)}" loading="lazy" src="{image_url}"><br>{post.realbody(None)}''')

	return Response("<?xml version=\"1.0\" encoding=\"UTF-8\"?>"+ doc.getvalue(), mimetype="application/xml")
