'''
Static files and uploaded images.

- GET /assets/<path> (also /static/assets/<path>) serves the site's own files: stylesheets, scripts, images, fonts and the like. Pages, and stylesheets themselves, link them with a "v" query parameter: the file's current version, which changes whenever the file does (a stylesheet's version covers those of the files it links).
- GET /images/<name> (also /hostedimages/<name> and /static/images/<name>) serves an uploaded image, under the name its URL was given when uploaded; a name ending ".WEBP" serves the ".webp" file of that name.
- GET /robots.txt serves the site's robots file, which is also /assets/robots.txt.

A file that doesn't exist, or a path reaching outside the files served, is 404.

Caching: an address that can only ever mean one version of the file is sent "Cache-Control: public, max-age=31536000" (a year): a site file asked for with its current version as "v", and an uploaded image (uploads never change under their name). Anything else, a site file asked for with no "v" or another one included, is sent "Cache-Control: no-cache" with an ETag, and asking again with that ETag in If-None-Match gets 304. WebP files are served as image/webp.
'''
import re

import pytest

from files.tests.spec.harness import *

LONG = "public, max-age=31536000"
ALIASES = ["/assets/", "/static/assets/"]


def _upload() -> str:
	'''The name an uploaded image was stored under.'''
	u = factories.user()
	as_user(u).post("/settings/images/profile", files={"profile": uploads.png(2, 2)})
	url = db.row("users", id=u["id"])["profileurl"]
	assert url.startswith("/images/")
	return url.removeprefix("/images/")


SITE_FILES = ["images/default-profile-pic.webp", "fonts/fa-brands-400.woff2", "fonts/fa-brands-400.ttf", "css/main.css", "js/bootstrap.js", "manifest_TheMotte.json", "robots.txt"]
# Where pages and stylesheets link site files
ASSET_LINK = re.compile(r"""(?:/assets/|\.\./)([^"'()\s?]+)(\?v=[^"'()\s&]*)?""")


def _linked_versions() -> dict[str, str]:
	'''The versions that the front page (showing a post by a user with the default picture) and its stylesheets link site files with.'''
	factories.post(factories.user())
	page = anon().get("/")
	texts = [page.text] + [anon().get(f"/assets/{path}{version}").text for path, version in ASSET_LINK.findall(page.text) if path.endswith(".css")]
	versions = {}
	for text in texts:
		for path, version in ASSET_LINK.findall(text):
			versions[path.removeprefix("css/../")] = version
	return versions


@pytest.mark.parametrize("prefix", ALIASES)
@pytest.mark.parametrize("path", ["images/default-profile-pic.webp", "fonts/fa-brands-400.woff2", "css/main.css", "js/bootstrap.js", "manifest_TheMotte.json"])
def test_site_files_asked_for_with_their_version_are_cached_for_a_year(path, prefix):
	version = _linked_versions()[path]

	r = anon().get(f"{prefix}{path}{version}")

	assert_status(r, 200)
	assert r.header("Cache-Control") == LONG


def test_pages_and_stylesheets_link_the_site_files_there_are_with_their_version():
	versions = _linked_versions()

	unversioned = [path for path, version in versions.items() if not version.startswith("?v=") or len(version) == 3]
	assert versions and all(anon().get(f"/assets/{path}").status == 404 for path in unversioned), f"linked without a version: {unversioned}"


@pytest.mark.parametrize("prefix", ALIASES)
@pytest.mark.parametrize("path", SITE_FILES)
@pytest.mark.parametrize("version", ["", "?v=1", "?v="], ids=["no version", "another version", "empty version"])
def test_site_files_asked_for_otherwise_are_revalidated(path, prefix, version):
	client = anon()
	r = client.get(prefix + path + version)

	assert_status(r, 200)
	assert r.header("Cache-Control") == "no-cache" and r.body
	assert_status(client.get(prefix + path + version, headers={"If-None-Match": r.header("ETag")}), 304)


def test_robots_txt_is_revalidated():
	r = anon().get("/robots.txt")

	assert r.header("Cache-Control") == "no-cache"


@pytest.mark.parametrize("path", ["images/default-profile-pic.webp", "css/main.css", "fonts/fa-brands-400.woff2"])
def test_both_addresses_serve_the_same_file(path):
	assert anon().get(f"/assets/{path}").body == anon().get(f"/static/assets/{path}").body


def test_site_webp_images_are_served_as_webp():
	assert_serves_image("/assets/images/default-profile-pic.webp")
	assert anon().get("/assets/images/default-profile-pic.webp").header("Content-Type") == "image/webp"


@pytest.mark.parametrize("path", ["/assets/images/nothing-here.webp", "/assets/../__main__.py", "/assets/%2e%2e/__main__.py", "/static/assets/../__main__.py", "/images/nothing-here.webp", "/images/..%2f__main__.py", "/images/%2e%2e"])
def test_missing_or_outside_files_are_not_found(path):
	assert_status(anon().get(path), 404)


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
	assert r.header("Content-Type").startswith("text/plain") and r.body == anon().get("/assets/robots.txt").body
