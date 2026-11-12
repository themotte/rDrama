'''
Static files and uploaded images.

- GET /assets/<path> (also /static/assets/<path>) serves the site's own files: stylesheets, scripts, images, fonts and the like. Which files there are, and their paths, are the implementation's own, except the default picture (DEFAULT_PICTURE), which stored rows name. Pages, and stylesheets themselves, link them with a "v" query parameter: the file's current version, which changes whenever the file does (a stylesheet's version covers those of the files it links).
- GET /images/<name> (also /hostedimages/<name> and /static/images/<name>) serves an uploaded image, under the name its URL was given when uploaded; a name ending ".WEBP" serves the ".webp" file of that name.
- GET /robots.txt serves the site's robots file, as plain text.

A file that doesn't exist, or a path reaching outside the files served, is 404.

Caching: an address that can only ever mean one version of the file is sent "Cache-Control: public, max-age=31536000" (a year): a site file asked for with its current version as "v", and an uploaded image (uploads never change under their name). Anything else, a site file asked for with no "v" or another one included, is sent "Cache-Control: no-cache" with an ETag, and asking again with that ETag in If-None-Match gets 304. WebP files are served as image/webp.
'''
import re
from urllib.parse import urljoin, urlsplit

import pytest

from files.tests.spec.harness import *

LONG = "public, max-age=31536000"
ALIASES = ["/assets/", "/static/assets/"]
DEFAULT_PICTURE_FILE = DEFAULT_PICTURE.removeprefix("/assets/")


def _upload() -> str:
	'''The name an uploaded image was stored under.'''
	u = factories.user()
	as_user(u).post("/settings/images/profile", files={"profile": uploads.png(2, 2)})
	url = db.row("users", id=u["id"])["profileurl"]
	assert url.startswith("/images/")
	return url.removeprefix("/images/")


# What a stylesheet refers to, outside its comments
CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
CSS_REFERENCE = re.compile(r"""url\(\s*(?:"([^"]*)"|'([^']*)'|([^)\s]*))\s*\)|@import\s+["']([^"']+)["']""")


def _linked() -> set[tuple[str, str]]:
	'''The site files the front page (showing a post by a user with the default picture) links or embeds, and those its stylesheets refer to, followed through: each file's path under /assets/ with each query it's linked with ("" for none).'''
	factories.post(factories.user())
	site = urlsplit(config.site_url()).netloc
	pending = [urljoin(config.site_url() + "/", address) for address in addresses(anon().get("/"))]
	found, read = set(), set()
	while pending:
		address = urlsplit(pending.pop(0))
		if address.netloc != site or not address.path.startswith("/assets/"):
			continue
		path, query = address.path.removeprefix("/assets/"), f"?{address.query}" if address.query else ""
		found.add((path, query))
		if path in read:
			continue
		read.add(path)
		r = anon().get(f"/assets/{path}{query}")
		if (r.header("Content-Type") or "").startswith("text/css"):
			references = [next(group for group in m.groups() if group is not None) for m in CSS_REFERENCE.finditer(CSS_COMMENT.sub("", r.text))]
			pending += [urljoin(address.geturl(), reference) for reference in references if not reference.startswith(("data:", "#"))]
	return found


def _versioned(linked: set[tuple[str, str]]) -> set[tuple[str, str]]:
	return {(path, query) for path, query in linked if query.startswith("?v=") and len(query) > 3}


def _versioned_files() -> set[str]:
	files = {path for path, _ in _versioned(_linked())}
	assert files, "the front page links no site file with its version"
	return files


@pytest.mark.parametrize("prefix", ALIASES)
def test_site_files_asked_for_with_their_version_are_cached_for_a_year(prefix):
	client = anon()
	linked = _versioned(_linked())
	answers = {(path, query): client.get(f"{prefix}{path}{query}") for path, query in linked}

	assert linked and {link: (r.status, r.header("Cache-Control")) for link, r in answers.items() if (r.status, r.header("Cache-Control")) != (200, LONG)} == {}


def test_pages_and_stylesheets_link_the_site_files_there_are_with_their_version():
	linked = _linked()

	unversioned = sorted(link for link in linked - _versioned(linked) if anon().get(f"/assets/{link[0]}").status != 404)
	assert linked and unversioned == [], f"linked without a version: {unversioned}"


@pytest.mark.parametrize("prefix", ALIASES)
@pytest.mark.parametrize("version", ["", "?v=1", "?v="], ids=["no version", "another version", "empty version"])
def test_site_files_asked_for_otherwise_are_revalidated(prefix, version):
	client = anon()
	wrong = {}
	for path in _versioned_files() | {DEFAULT_PICTURE_FILE}:
		r = client.get(prefix + path + version)
		again = client.get(prefix + path + version, headers={"If-None-Match": r.header("ETag") or ""}) if r.status == 200 else None
		if (r.status, r.header("Cache-Control"), bool(r.body), again and again.status) != (200, "no-cache", True, 304):
			wrong[path] = (r.status, r.header("Cache-Control"), again and again.status)

	assert wrong == {}


def test_robots_txt_is_revalidated():
	r = anon().get("/robots.txt")

	assert r.header("Cache-Control") == "no-cache"


def test_both_addresses_serve_the_same_file():
	client = anon()
	paths = _versioned_files() | {DEFAULT_PICTURE_FILE}

	assert [path for path in paths if not client.get(f"/assets/{path}").body or client.get(f"/static/assets/{path}").body != client.get(f"/assets/{path}").body] == []


def test_the_default_picture_is_served_as_webp():
	assert_serves_image(DEFAULT_PICTURE)
	assert anon().get(DEFAULT_PICTURE).header("Content-Type") == "image/webp"


def _outside() -> str:
	'''A file that exists outside the files served (the site settings), as a path climbing to it from more directories deep than any served one is.'''
	path = config.site_settings_path()
	assert path.startswith("/"), "the site settings path isn't absolute"
	return "../" * 24 + path.lstrip("/")


@pytest.mark.parametrize("path", [
	lambda: "/assets/images/nothing-here.webp",
	lambda: "/assets/" + _outside(),
	lambda: "/assets/" + _outside().replace("..", "%2e%2e"),
	lambda: "/static/assets/" + _outside(),
	lambda: "/images/nothing-here.webp",
	lambda: "/images/" + _outside().replace("/", "%2f"),
	lambda: "/images/%2e%2e",
], ids=["missing", "outside", "outside, escaped", "outside, other address", "missing image", "outside the images", "the images' parent"])
def test_missing_or_outside_files_are_not_found(path):
	assert_status(anon().get(path()), 404)


@pytest.mark.parametrize("prefix", ["/images/", "/hostedimages/", "/static/images/"])
def test_uploaded_images_are_served_and_cached_for_a_year(prefix):
	name = _upload()

	r = anon().get(prefix + name)

	assert_serves_image(prefix + name)
	assert r.header("Content-Type") == "image/webp" and r.header("Cache-Control") == LONG


def test_an_uppercase_webp_name_serves_the_webp_file():
	name = _upload()

	r = anon().get("/images/" + name.removesuffix(".webp") + ".WEBP")

	assert_status(r, 200)
	assert r.body == anon().get("/images/" + name).body


def test_robots_txt_is_the_sites_robots_file():
	r = anon().get("/robots.txt")

	assert_status(r, 200)
	assert r.header("Content-Type").startswith("text/plain") and r.body
