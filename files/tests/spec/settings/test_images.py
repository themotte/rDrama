'''
Avatar (POST /settings/images/profile, field "profile") and banner (POST /settings/images/banner, field "banner") uploads.

Uploads are stored by the site and served under /images/ as WebP, without the metadata they arrived with (EXIF, GPS, XMP, text chunks, colour profiles). An animated GIF or WebP stays animated, its frames' timing and its loop count kept; anything else is stored as its first picture (of a phone's multi-picture photo, an animated PNG or a multi-page TIFF), turned upright by its EXIF orientation, or as it is when its EXIF can't be read. An image more than 16383 pixels wide or high is refused (400), as is one that can't be read whole, and neither is stored. Replacing an uploaded image deletes the old file; images hosted elsewhere (any URL not starting with /images/ or <site>/images/) are simply replaced.
'''
import os
from io import BytesIO

import pytest
from PIL import Image

from files.tests.spec.harness import *


def _width(url):
	return Image.open(BytesIO(anon().get(url).body)).width


def test_avatar_upload_sets_full_size_and_thumbnail_images():
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).post("/settings/images/profile", files={"profile": uploads.png(2, 2)})

	assert_html(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {"highres": ANY, "profileurl": ANY}}})
	row = db.row("users", id=u["id"])
	assert row["highres"] != row["profileurl"]
	assert_serves_image(row["highres"])
	assert_serves_image(row["profileurl"])


def test_avatar_thumbnail_is_at_most_100_pixels_wide():
	u = factories.user()

	assert_html(as_user(u).post("/settings/images/profile", files={"profile": uploads.png(300, 200)}), 200)

	row = db.row("users", id=u["id"])
	assert _width(row["highres"]) == 300
	assert _width(row["profileurl"]) == 100


def test_avatar_replacement_deletes_the_previous_uploads():
	u = factories.user()
	client = as_user(u)
	client.post("/settings/images/profile", files={"profile": uploads.png(2, 2)})
	old = db.row("users", id=u["id"])

	assert_html(client.post("/settings/images/profile", files={"profile": uploads.png(2, 2)}), 200)

	assert_status(anon().get(old["highres"]), 404)
	assert_status(anon().get(old["profileurl"]), 404)


def test_avatar_upload_replaces_an_externally_hosted_avatar():
	u = factories.user(profileurl="https://example.com/a.webp", highres="https://example.com/b.webp")

	with db_diff() as d:
		r = as_user(u).post("/settings/images/profile", files={"profile": uploads.png(2, 2)})

	assert_html(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {"highres": ANY, "profileurl": ANY}}})


def test_avatar_upload_without_a_file_is_rejected():
	assert_status(as_user(factories.user()).post("/settings/images/profile", headers=XHR), 400)


@pytest.mark.parametrize("path, field", [("/settings/images/profile", "profile"), ("/settings/images/banner", "banner")])
@pytest.mark.parametrize("upload", [uploads.not_an_image(), uploads.truncated_png(), uploads.oversized_png()], ids=["garbage", "truncated", "oversized"])
def test_unreadable_images_are_rejected(path, field, upload):
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).post(path, files={field: upload}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


def test_banner_upload():
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).post("/settings/images/banner", files={"banner": uploads.png(2, 2)})

	assert_html(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {"bannerurl": ANY}}})
	assert_serves_image(db.row("users", id=u["id"])["bannerurl"])


def test_banner_replacement_deletes_the_previous_upload():
	u = factories.user()
	client = as_user(u)
	client.post("/settings/images/banner", files={"banner": uploads.png(2, 2)})
	old = db.row("users", id=u["id"])["bannerurl"]

	assert_html(client.post("/settings/images/banner", files={"banner": uploads.png(2, 2)}), 200)

	assert_status(anon().get(old), 404)


def test_gif_uploads_are_converted_keeping_their_animation():
	u = factories.user()

	assert_html(as_user(u).post("/settings/images/banner", files={"banner": uploads.gif(4, 4)}), 200)

	url = db.row("users", id=u["id"])["bannerurl"]
	assert_serves_image(url)
	served = Image.open(BytesIO(anon().get(url).body))
	assert served.format == "WEBP" and served.n_frames == 2


def test_replacing_an_image_hosted_elsewhere_deletes_nothing_here():
	victim = factories.user()
	as_user(victim).post("/settings/images/banner", files={"banner": uploads.png(2, 2)})
	victim_url = db.row("users", id=victim["id"])["bannerurl"]
	u = factories.user(bannerurl=f"https://elsewhere.example{victim_url}")

	assert_html(as_user(u).post("/settings/images/banner", files={"banner": uploads.png(2, 2)}), 200)

	assert_serves_image(victim_url)


def _no_identifying_metadata(url: str, marker: str) -> bool:
	body = anon().get(url).body
	served = Image.open(BytesIO(body))
	return marker.encode() not in body and not served.getexif() and not served.info.get("xmp")


@pytest.mark.parametrize("image_format", ["JPEG", "PNG", "WEBP"])
@pytest.mark.parametrize("field, columns", [("banner", ["bannerurl"]), ("profile", ["highres", "profileurl"])], ids=["banner", "avatar"])
def test_uploaded_images_lose_identifying_metadata(image_format, field, columns):
	u = factories.user()
	marker = factories.unique("marker")

	assert_html(as_user(u).post(f"/settings/images/{field}", files={field: uploads.photo(image_format, 200, 150, marker)}), 200)

	row = db.row("users", id=u["id"])
	assert [column for column in columns if not _no_identifying_metadata(row[column], marker)] == []


def test_a_photo_holding_a_second_picture_is_stored_as_its_first_upright():
	u = factories.user()

	assert_html(as_user(u).post("/settings/images/banner", files={"banner": uploads.multi_picture_jpeg(8, 6, orientation=6)}), 200)

	served = Image.open(BytesIO(anon().get(db.row("users", id=u["id"])["bannerurl"]).body))
	red, _, blue = served.convert("RGB").getpixel((0, 0))
	assert (getattr(served, "n_frames", 1), served.size, red > 200 > blue) == (1, (6, 8), True)


@pytest.mark.parametrize("image_format", ["GIF", "WEBP"])
def test_an_animation_keeps_its_frames_timing_and_loop_count(image_format):
	u = factories.user()

	assert_html(as_user(u).post("/settings/images/banner", files={"banner": uploads.animation(image_format, [100, 500, 1000], loop=2)}), 200)

	served = Image.open(BytesIO(anon().get(db.row("users", id=u["id"])["bannerurl"]).body))
	durations = []
	for frame in range(served.n_frames):
		served.seek(frame)
		served.load()
		durations.append(served.info["duration"])
	assert (durations, served.info["loop"]) == ([100, 500, 1000], 2)


def test_an_image_whose_exif_cant_be_read_is_stored_as_it_is():
	u = factories.user()

	assert_html(as_user(u).post("/settings/images/banner", files={"banner": uploads.unreadable_exif_webp()}), 200)

	assert_serves_image(db.row("users", id=u["id"])["bannerurl"])


def test_an_image_too_wide_to_store_is_refused():
	u = factories.user()

	with db_diff() as d:
		r = as_user(u).post("/settings/images/banner", files={"banner": uploads.too_wide_png()})

	assert_status(r, 400)
	d.assert_exactly()
	assert os.listdir(config.images_dir()) == []
