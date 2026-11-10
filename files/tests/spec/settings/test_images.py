'''
Avatar (POST /settings/images/profile, field "profile") and banner (POST /settings/images/banner, field "banner") uploads.

Uploads are stored by the site and served under /images/ as WebP. Replacing an uploaded image deletes the old file; images hosted elsewhere (any URL not starting with /images/ or <site>/images/) are simply replaced.
'''
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


def test_uploaded_photos_lose_identifying_metadata():
	u = factories.user()
	photo = Image.new("RGB", (4, 4), "red")
	exif = Image.Exif()
	exif[0x010F] = "SpyCam"  # camera make
	exif[0x0131] = "Tracker 1.0"  # software
	exif[0x0112] = 1  # orientation, which is honored rather than stripped
	data = BytesIO()
	photo.save(data, format="JPEG", exif=exif)

	assert_html(as_user(u).post("/settings/images/banner", files={"banner": ("photo.jpg", data.getvalue(), "image/jpeg")}), 200)

	served = Image.open(BytesIO(anon().get(db.row("users", id=u["id"])["bannerurl"]).body))
	assert not {0x010F, 0x0131} & set(served.getexif())
