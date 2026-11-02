'''
POST /settings/profile, free-text fields: bio, friends list, enemies list.

These come after the preference toggles in the single-choice order: clearing (an empty bio without an image upload, then empty friends, enemies), then friends, enemies, bio. Each renders the profile settings page, and ignores any preference "multi" fields in the same request.
'''
import pytest

from files.tests.spec.harness import *


def _post(user, data, headers=None, files=None):
	return as_user(user).post("/settings/profile", data, headers=headers, files=files)


@pytest.mark.parametrize("field", ["bio", "friends", "enemies"])
def test_empty_text_field_clears_it(field):
	u = factories.user(**{field: "old", f"{field}_html": "<p>old</p>"})

	with db_diff() as d:
		r = _post(u, {field: ""})

	assert_html(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {field: None, f"{field}_html": None}}})


def test_bio_is_stored_with_rendered_html():
	u = factories.user()
	token = factories.unique()

	with db_diff() as d:
		r = _post(u, {"bio": f"**{token}**"})

	assert_html(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {"bio": f"**{token}**", "bio_html": ANY}}})
	html = db.row("users", id=u["id"])["bio_html"]
	assert token in html and "**" not in html


def test_bio_is_truncated_to_1500_characters_before_rendering():
	u = factories.user()
	beyond = factories.unique()

	with db_diff() as d:
		_post(u, {"bio": "a" * 1500 + beyond})

	d.assert_exactly(updated={"users": {u["id"]: {"bio": "a" * 1500, "bio_html": ANY}}})
	assert beyond not in db.row("users", id=u["id"])["bio_html"]


def test_bio_text_fields_ignore_preference_fields():
	u = factories.user(frontsize=25)

	with db_diff() as d:
		_post(u, {"bio": "hello", "frontsize": "50"})

	d.assert_exactly(updated={"users": {u["id"]: {"bio": "hello", "bio_html": ANY}}})


def test_bio_image_is_appended_as_markdown_image():
	u = factories.user()
	token = factories.unique()

	with db_diff() as d:
		r = _post(u, {"bio": token}, files={"file": uploads.png(2, 2)})

	assert_html(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {"bio": ANY, "bio_html": ANY}}})
	bio = db.row("users", id=u["id"])["bio"]
	assert bio.startswith(f"{token}\n\n![](") and bio.endswith(")")
	assert_serves_image(bio[len(f"{token}\n\n![]("):-1])


def test_bio_image_survives_a_full_length_bio():
	u = factories.user()

	assert_html(_post(u, {"bio": "a" * 1600}, files={"file": uploads.png(2, 2)}), 200)

	bio = db.row("users", id=u["id"])["bio"]
	text, image = bio.split("\n\n![](")
	assert len(bio) == 1500 and set(text) == {"a"}
	assert_serves_image(image[:-1])


@pytest.mark.parametrize("data", [{}, {"bio": ""}], ids=["no bio field", "empty bio"])
def test_bio_image_alone_becomes_the_bio(data):
	u = factories.user(bio="old", bio_html="<p>old</p>")

	r = _post(u, data, files={"file": uploads.png(2, 2)})

	assert_html(r, 200)
	assert db.row("users", id=u["id"])["bio"].startswith("\n\n![](/")


def test_bio_upload_of_a_non_image_type_is_refused():
	u = factories.user()

	with db_diff() as d:
		r = _post(u, {"bio": factories.unique()}, files={"file": uploads.text_file()})

	assert_html(r, 400)
	d.assert_exactly()


def test_bio_upload_of_a_non_image_type_is_refused_as_json_for_scripts():
	r = _post(factories.user(), {"bio": factories.unique()}, files={"file": uploads.text_file()}, headers=XHR)

	assert_status(r, 400)
	assert r.json["code"] == 400


@pytest.mark.parametrize("upload", [uploads.not_an_image(), uploads.truncated_png(), uploads.oversized_png()], ids=["garbage", "truncated", "oversized"])
def test_bio_upload_of_an_unreadable_image_is_refused(upload):
	u = factories.user()

	with db_diff() as d:
		r = _post(u, {"bio": factories.unique()}, files={"file": upload}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


def test_bio_image_through_tor_is_dropped_but_the_text_saved():
	u = factories.user()
	token = factories.unique()

	with db_diff() as d:
		r = _post(u, {"bio": token}, files={"file": uploads.png(2, 2)}, headers=TOR)

	assert_html(r, 200)
	d.assert_exactly(updated={"users": {u["id"]: {"bio": token, "bio_html": ANY}}})


def test_bio_image_alone_through_tor_changes_nothing():
	u = factories.user()

	with db_diff() as d:
		r = _post(u, {}, files={"file": uploads.png(2, 2)}, headers={**XHR, **TOR})

	assert_status(r, 400)
	d.assert_exactly()


@pytest.mark.parametrize("field", ["friends", "enemies"])
def test_relationship_list_is_stored_and_mentioned_users_are_notified(field):
	friend = factories.user()
	u = factories.user()
	text = f"@{friend['username']} is listed"

	with db_diff() as d:
		r = _post(u, {field: text})

	assert_html(r, 200)
	d.assert_exactly(
		updated={"users": {u["id"]: {field: text, f"{field}_html": ANY}}},
		inserted={
			"comments": [{"author_id": seed.SYSTEM_ID, "parent_submission": None}],
			"notifications": [{"user_id": friend["id"], "read": False}],
		},
	)
	notification = db.row("comments", author_id=seed.SYSTEM_ID)
	assert u["username"] in notification["body_html"]


@pytest.mark.parametrize("field", ["friends", "enemies"])
def test_relationship_list_notification_is_reused_for_later_mentions(field):
	friend, other = factories.user(), factories.user()
	u = factories.user()
	_post(u, {field: f"@{friend['username']}"})

	with db_diff() as d:
		_post(u, {field: f"@{friend['username']} @{other['username']}"})

	d.assert_exactly(
		updated={"users": {u["id"]: {field: ANY, f"{field}_html": ANY}}},
		inserted={"notifications": [{"user_id": other["id"]}]},
	)


def test_friends_and_enemies_notifications_are_separate():
	listed = factories.user()
	u = factories.user()

	_post(u, {"friends": f"@{listed['username']}"})
	_post(u, {"enemies": f"@{listed['username']}"})

	assert len({n["comment_id"] for n in db.rows("notifications", user_id=listed["id"])}) == 2


@pytest.mark.parametrize("field", ["friends", "enemies"])
@pytest.mark.parametrize("blocker", ["listed", "lister"])
def test_relationship_list_does_not_notify_across_a_block(field, blocker):
	listed = factories.user()
	u = factories.user()
	if blocker == "listed":
		db.insert("userblocks", user_id=listed["id"], target_id=u["id"])
	else:
		db.insert("userblocks", user_id=u["id"], target_id=listed["id"])

	with db_diff() as d:
		_post(u, {field: f"@{listed['username']}"})

	d.assert_exactly(updated={"users": {u["id"]: {field: ANY, f"{field}_html": ANY}}})


@pytest.mark.parametrize("field", ["friends", "enemies"])
def test_relationship_list_does_not_notify_yourself(field):
	u = factories.user()

	with db_diff() as d:
		_post(u, {field: f"@{u['username']}"})

	d.assert_exactly(updated={"users": {u["id"]: {field: ANY, f"{field}_html": ANY}}})


@pytest.mark.parametrize("field", ["friends", "enemies"])
def test_relationship_list_is_truncated_to_500_characters(field):
	u = factories.user()

	with db_diff() as d:
		_post(u, {field: "a" * 600})

	d.assert_exactly(updated={"users": {u["id"]: {field: "a" * 500, f"{field}_html": ANY}}})
