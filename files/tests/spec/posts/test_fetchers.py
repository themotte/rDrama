'''
Things the site looks up on other sites or in its own posts for the submit form and new link posts:
- POST /is_repost with "url": the permalink of a live post already linking there, or "" (no login needed).
- GET /submit/title?url=...: the <title> of the page at url, for prefilling the title field.
- The thumbnail of a new link post, fetched in the background from the linked page's preview-image metadata, its images, or the link itself when it is an image.
'''
import pytest

from files.tests.spec.harness import *


# Reposts

def _is_repost(url):
	return anon().post("/is_repost", {"url": url})


@pytest.mark.parametrize("asked", [
	"https://example.com/page",
	"http://example.com/page",
	"https://example.com/page/",
	"https://EXAMPLE.com/page",
	"https://example.com/page?utm_source=feed&ref_src=x",
], ids=["same", "http", "trailing slash", "case", "tracking parameters"])
def test_repost_check_finds_posts_linking_to_the_same_page(asked):
	post = factories.post(factories.user(), url="https://example.com/page")

	r = _is_repost(asked)

	assert_status(r, 200)
	assert r.json == {"permalink": f"http://{config.site_host()}/post/{post['id']}/{post['title']}"}


@pytest.mark.parametrize("state", [{"state_mod": "REMOVED"}, {"state_mod": "FILTERED"}, {"state_user_deleted_utc": "2020-01-01T00:00:00Z"}], ids=["removed", "filtered", "deleted"])
def test_repost_check_ignores_posts_that_are_not_live(state):
	factories.post(factories.user(), url="https://example.com/page", **state)

	assert _is_repost("https://example.com/page").json == {"permalink": ""}


@pytest.mark.parametrize("stored, asked", [
	("http://example.com/page", "https://example.com/page"),
	("https://example.com/page/", "https://example.com/page"),
	("https://example.com/a%20b", "https://example.com/a%20b"),
	("https://example.com/a_b", "https://example.com/a_b"),
], ids=["stored as http", "stored with trailing slash", "percent escape", "underscore"])
def test_repost_check_matches_variants_of_the_earlier_link(stored, asked):
	post = factories.post(factories.user(), url=stored)

	assert _is_repost(asked).json["permalink"].startswith(f"http://{config.site_host()}/post/{post['id']}/")


def test_repost_check_distinguishes_letter_case_in_paths():
	factories.post(factories.user(), url="https://example.com/AbC")

	assert _is_repost("https://example.com/abc").json == {"permalink": ""}


def test_repost_check_does_not_treat_underscores_as_wildcards():
	factories.post(factories.user(), url="https://example.com/aXb")

	assert _is_repost("https://example.com/a_b").json == {"permalink": ""}


def test_repost_check_finds_the_earliest_post():
	earliest = factories.post(factories.user(), url="https://example.com/page")
	factories.post(factories.user(), url="https://example.com/page")

	assert _is_repost("https://example.com/page").json["permalink"].startswith(f"http://{config.site_host()}/post/{earliest['id']}/")


@pytest.mark.parametrize("hidden", ["draft", "shadowbanned author"])
def test_repost_check_ignores_posts_others_cannot_see(hidden):
	author = factories.user(shadowbanned="somemod" if hidden == "shadowbanned author" else None)
	factories.post(author, url="https://example.com/page", private=hidden == "draft")

	assert _is_repost("https://example.com/page").json == {"permalink": ""}


def test_repost_check_keeps_meaningful_query_parameters():
	factories.post(factories.user(), url="https://example.com/page?id=1")

	assert _is_repost("https://example.com/page?id=2").json == {"permalink": ""}


@pytest.mark.parametrize("fields", [{}, {"url": "http://["}], ids=["missing", "malformed"])
def test_repost_check_needs_a_url(fields):
	assert_status(anon().post("/is_repost", fields), 400)


# Page titles

def _title(client, url):
	return client.get("/submit/title", params={"url": url}, headers=XHR)


@pytest.mark.parametrize("asked", ["https://example.com/page", "  https://example.com/page  "], ids=["plain", "surrounded by spaces"])
def test_page_title_is_fetched(asked):
	external_web.serve("https://example.com/page", headers={"Content-Type": "text/html; charset=utf-8"}, body="<html><head><title>Fish &amp; Chips</title></head></html>")

	r = _title(as_user(factories.user()), asked)

	assert_status(r, 200)
	assert r.json == {"url": "https://example.com/page", "title": "Fish & Chips"}


@pytest.mark.parametrize("url", ["", "example.com/page", "https://example.com/a\\b", "https://example.com/photo.JPG", "https://example.com/clip.mp4?size=large"], ids=["empty", "no scheme", "backslash", "image", "video with query"])
def test_page_title_is_not_fetched_for_unsuitable_links(url):
	assert_status(_title(as_user(factories.user()), url), 400)


@pytest.mark.parametrize("response", [
	{"headers": {"Content-Type": "application/pdf"}, "body": "<title>x</title>"},
	{"headers": {}, "body": "<title>x</title>"},
	{"headers": {"Content-Type": "text/html"}, "body": "<p>untitled</p>"},
	{"headers": {"Content-Type": "text/html"}, "body": "<title></title>"},
], ids=["not html", "no content type", "no title", "empty title"])
def test_pages_without_a_usable_title_give_none(response):
	external_web.serve("https://example.com/page", **response)

	assert_status(_title(as_user(factories.user()), "https://example.com/page"), 400)


def test_unreachable_pages_give_no_title():
	external_web.unreachable("https://example.com/page")

	assert_status(_title(as_user(factories.user()), "https://example.com/page"), 400)


def test_page_titles_need_a_login():
	assert_api_unauthorized(_title(anon(), "https://example.com/page"))


# Thumbnails

def _link_post(url):
	_submit_client = as_user(factories.user())
	assert_html(_submit_client.post("/submit", {"title": factories.unique("title"), "url": url}), 200)
	return db.rows("submissions")[-1]


def _thumbnail_of(post):
	return db.row("submissions", id=post["id"])["thumburl"]


def _png(size):
	return uploads.png(size, size)[1]


def _html(head="", body=""):
	return {"headers": {"Content-Type": "text/html"}, "body": f"<html><head>{head}</head><body>{body}</body></html>"}


def _image(size=64):
	return {"headers": {"Content-Type": "image/png"}, "body": _png(size)}


def test_link_posts_get_a_thumbnail_from_the_page_preview_image():
	external_web.serve("https://example.com/article", **_html(head='<meta property="og:image" content="https://cdn.example.com/preview.png">'))
	external_web.serve("https://cdn.example.com/preview.png", **_image())
	post = _link_post("https://example.com/article")
	assert _thumbnail_of(post) is None

	run_background_work()

	thumbnail = _thumbnail_of(post)
	assert thumbnail.startswith("/images/")
	assert_serves_image(thumbnail)


@pytest.mark.parametrize("tag", [
	'<meta name="themotte:thumbnail" content="https://cdn.example.com/a.png">',
	'<meta name="twitter:image" content="https://cdn.example.com/a.png">',
	'<meta property="twitter:image" content="https://cdn.example.com/a.png">',
	'<meta name="thumbnail" content="https://cdn.example.com/a.png">',
], ids=["site", "twitter name", "twitter property", "generic"])
def test_preview_image_metadata_variants_are_recognized(tag):
	external_web.serve("https://example.com/article", **_html(head=tag))
	external_web.serve("https://cdn.example.com/a.png", **_image())
	post = _link_post("https://example.com/article")

	run_background_work()

	assert _thumbnail_of(post) is not None


def test_preview_images_are_tried_in_order_of_preference():
	external_web.serve("https://example.com/article", **_html(head=(
		'<meta property="og:image" content="https://cdn.example.com/og.png">'
		'<meta name="themotte:thumbnail" content="https://cdn.example.com/site.png">'
	)))
	external_web.serve("https://cdn.example.com/site.png", **_image())
	external_web.serve("https://cdn.example.com/og.png", **_image())
	_link_post("https://example.com/article")

	run_background_work()

	assert [url for _, url in external_web.requests()] == ["https://example.com/article", "https://cdn.example.com/site.png"]


def test_page_images_are_used_when_there_is_no_preview_image():
	external_web.serve("https://example.com/article", **_html(body='<img src="https://cdn.example.com/pic.png">'))
	external_web.serve("https://cdn.example.com/pic.png", **_image())
	post = _link_post("https://example.com/article")

	run_background_work()

	assert _thumbnail_of(post) is not None


@pytest.mark.parametrize("src, fetched", [
	("//cdn.example.com/pic.png", "https://cdn.example.com/pic.png"),
	("/pic.png", "https://example.com/pic.png"),
	("pic.png", "https://example.com/dir/pic.png"),
	("../pic.png", "https://example.com/pic.png"),
	("http://cdn.example.com/pic.png", "http://cdn.example.com/pic.png"),
], ids=["scheme-relative", "site-relative", "page-relative", "parent-relative", "absolute http"])
def test_image_addresses_resolve_against_the_page(src, fetched):
	external_web.serve("https://example.com/dir/article", **_html(body=f'<img src="{src}">'))
	external_web.serve(fetched, **_image())
	post = _link_post("https://example.com/dir/article")

	run_background_work()

	assert _thumbnail_of(post) is not None


@pytest.mark.parametrize("bad", [
	{"status": 404, **_image()},
	{"headers": {"Content-Type": "text/html"}, "body": "<p>not an image</p>"},
	{"headers": {"Content-Type": "image/svg+xml"}, "body": "<svg/>"},
	_image(size=20),
], ids=["missing", "not an image", "svg", "too small"])
def test_unsuitable_candidates_are_skipped(bad):
	external_web.serve("https://example.com/article", **_html(body='<img src="https://cdn.example.com/bad"><img src="https://cdn.example.com/good.png">'))
	external_web.serve("https://cdn.example.com/bad", **bad)
	external_web.serve("https://cdn.example.com/good.png", **_image())
	post = _link_post("https://example.com/article")

	run_background_work()

	assert _thumbnail_of(post) is not None
	assert [url for _, url in external_web.requests()][-1] == "https://cdn.example.com/good.png"


_UNUSABLE_IMAGES = {
	"over 8 MB": lambda: uploads.noisy_png(1700, 1700)[1],
}


@pytest.mark.parametrize("bad", list(_UNUSABLE_IMAGES))
def test_unusable_images_are_skipped(bad):
	external_web.serve("https://example.com/article", **_html(body='<img src="https://cdn.example.com/bad.png"><img src="https://cdn.example.com/good.png">'))
	external_web.serve("https://cdn.example.com/bad.png", headers={"Content-Type": "image/png"}, body=_UNUSABLE_IMAGES[bad]())
	external_web.serve("https://cdn.example.com/good.png", **_image())
	post = _link_post("https://example.com/article")

	run_background_work()

	assert _thumbnail_of(post) is not None
	assert [url for _, url in external_web.requests()][-1] == "https://cdn.example.com/good.png"


def test_image_addresses_that_are_not_web_addresses_are_skipped():
	external_web.serve("https://example.com/article", **_html(body='<img src="data:image/png;base64,AAAA"><img src="https://cdn.example.com/good.png">'))
	external_web.serve("https://cdn.example.com/good.png", **_image())
	post = _link_post("https://example.com/article")

	run_background_work()

	assert _thumbnail_of(post) is not None


@pytest.mark.parametrize("image", ["over 8 MB"])
def test_links_to_unusable_images_give_no_thumbnail(image):
	external_web.serve("https://example.com/photo", headers={"Content-Type": "image/png"}, body=_UNUSABLE_IMAGES[image]())
	post = _link_post("https://example.com/photo")

	run_background_work()

	assert _thumbnail_of(post) is None


def test_unreachable_candidates_are_skipped():
	external_web.serve("https://example.com/article", **_html(body='<img src="https://cdn.example.com/bad.png"><img src="https://cdn.example.com/good.png">'))
	external_web.unreachable("https://cdn.example.com/bad.png")
	external_web.serve("https://cdn.example.com/good.png", **_image())
	post = _link_post("https://example.com/article")

	run_background_work()

	assert _thumbnail_of(post) is not None


def test_images_at_least_30_pixels_square_qualify():
	external_web.serve("https://example.com/article", **_html(body='<img src="https://cdn.example.com/narrow.png"><img src="https://cdn.example.com/square.png">'))
	external_web.serve("https://cdn.example.com/narrow.png", headers={"Content-Type": "image/png"}, body=uploads.png(30, 29)[1])
	external_web.serve("https://cdn.example.com/square.png", **_image(size=30))
	post = _link_post("https://example.com/article")

	run_background_work()

	assert _thumbnail_of(post) is not None
	assert [url for _, url in external_web.requests()][-1] == "https://cdn.example.com/square.png"


def test_pages_without_suitable_images_give_no_thumbnail():
	external_web.serve("https://example.com/article", **_html(body='<img src="https://cdn.example.com/tiny.png">'))
	external_web.serve("https://cdn.example.com/tiny.png", **_image(size=10))
	post = _link_post("https://example.com/article")

	run_background_work()

	assert _thumbnail_of(post) is None


def test_links_to_images_are_their_own_thumbnail():
	external_web.serve("https://example.com/photo", **_image())
	post = _link_post("https://example.com/photo")

	run_background_work()

	assert_serves_image(_thumbnail_of(post))


@pytest.mark.parametrize("page", [
	{"status": 500, **_html(head='<meta property="og:image" content="https://cdn.example.com/a.png">')},
	{"headers": {"Content-Type": "application/pdf"}, "body": "%PDF"},
], ids=["error status", "neither page nor image"])
def test_links_that_are_neither_pages_nor_images_give_no_thumbnail(page):
	external_web.serve("https://example.com/thing", **page)
	post = _link_post("https://example.com/thing")

	run_background_work()

	assert _thumbnail_of(post) is None


def test_unreachable_links_give_no_thumbnail():
	external_web.unreachable("https://example.com/gone")
	post = _link_post("https://example.com/gone")

	run_background_work()

	assert _thumbnail_of(post) is None


def test_text_and_image_posts_fetch_nothing():
	client = as_user(factories.user())
	assert_html(client.post("/submit", {"title": "t", "body": "text"}), 200)
	assert_html(client.post("/submit", {"title": "t2"}, files={"file": uploads.png(64, 64)}), 200)

	run_background_work()

	assert external_web.requests() == []
