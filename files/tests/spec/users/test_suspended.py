'''
What suspended users may do. While a ban runs (permanently, or until its end time), a user can't change their content or their public profile, or start following anyone. Each of these is refused with 403 and changes nothing:
- their posts and comments: publishing a draft (POST /publish/<post id>), editing (POST /edit_post/<post id>, POST /edit_comment/<comment id>), restoring deleted ones (POST /undelete_post/<post id>, POST /undelete/comment/<comment id>), marking them NSFW (POST /toggle_post_nsfw/<post id>, POST /toggle_comment_nsfw/<comment id>), and pinning a post to their profile (POST /pin/<post id>);
- their profile: setting or clearing the bio or friends text (POST /settings/profile with "bio" or "friends"), the name, flair, verified-badge colors (POST /settings/namecolor, /settings/titlecolor, /settings/verifiedcolor), the profile picture and banner (POST /settings/images/profile, /settings/images/banner), the profile page's CSS (POST /settings/profilecss), the username (POST /settings/name_change) and the flair text (POST /settings/title_change);
- following someone (POST /follow/<username>), which tells them;
- making their profile private or public (POST /id/<their id>/private/<0|1>; settings/test_privacy.py).
(Posting and commenting are refused too; see the posts and comments areas. Voting and reporting follow their own rules; see those areas.)

Everything else still works: deleting their own content, saving, subscribing, unfollowing and removing followers (which tell the other user, as ever), blocking, and their private preferences. Once a temporary ban has run out, nothing is refused.

A suspended admin is refused their admin actions too, and reads admin pages as before (harness/routes.py, admin(n); reporting/test_reports.py, the "!" reason; auth/test_session.py, read-only mode).
'''
import time

import pytest

from files.tests.spec.harness import *

DELETED = "2020-01-01T00:00:00Z"


def _suspended(permanently=False, **overrides):
	return factories.user(is_banned=factories.admin(2)["id"], unban_utc=0 if permanently else int(time.time()) + 86400, **overrides)


def _expired(**overrides):
	return factories.user(is_banned=factories.admin(2)["id"], unban_utc=int(time.time()) - 60, **overrides)


def _own_comment(v, **overrides):
	return factories.comment(v, factories.post(factories.user()), **overrides)


# Each case builds what the request needs for the suspended user `v` and returns (path, form fields, files)
CONTENT = {
	"publish": lambda v: (f"/publish/{factories.post(v, private=True)['id']}", {}, None),
	"edit post": lambda v: (lambda p: (f"/edit_post/{p['id']}", {"title": p["title"], "body": factories.unique()}, None))(factories.post(v)),
	"undelete post": lambda v: (f"/undelete_post/{factories.post(v, state_user_deleted_utc=DELETED)['id']}", {}, None),
	"post nsfw": lambda v: (f"/toggle_post_nsfw/{factories.post(v)['id']}", {}, None),
	"comment nsfw": lambda v: (f"/toggle_comment_nsfw/{_own_comment(v)['id']}", {}, None),
	"pin post": lambda v: (f"/pin/{factories.post(v)['id']}", {}, None),
	"edit comment": lambda v: (f"/edit_comment/{_own_comment(v)['id']}", {"body": factories.unique()}, None),
	"undelete comment": lambda v: (f"/undelete/comment/{_own_comment(v, state_user_deleted_utc=DELETED)['id']}", {}, None),
}

PROFILE = {
	"set bio": lambda v: ("/settings/profile", {"bio": factories.unique()}, None),
	"clear bio": lambda v: ("/settings/profile", {"bio": ""}, None),
	"bio image": lambda v: ("/settings/profile", {}, {"file": uploads.png(10, 10)}),
	"set friends": lambda v: ("/settings/profile", {"friends": factories.unique()}, None),
	"clear friends": lambda v: ("/settings/profile", {"friends": ""}, None),
	"name color": lambda v: ("/settings/namecolor", {"color": "123456"}, None),
	"flair color": lambda v: ("/settings/titlecolor", {"titlecolor": "123456"}, None),
	"verified color": lambda v: ("/settings/verifiedcolor", {"verifiedcolor": "123456"}, None),
	"profile picture": lambda v: ("/settings/images/profile", {}, {"profile": uploads.png(10, 10)}),
	"banner": lambda v: ("/settings/images/banner", {}, {"banner": uploads.png(10, 10)}),
	"profile css": lambda v: ("/settings/profilecss", {"profilecss": "body {}"}, None),
	"username": lambda v: ("/settings/name_change", {"name": factories.unique("renamed")}, None),
	"flair": lambda v: ("/settings/title_change", {"title": factories.unique()}, None),
	"follow": lambda v: (f"/follow/{factories.user()['username']}", {}, None),
}


def _refused(case, ban):
	v = _suspended(permanently=ban == "permanent", bio="old bio", bio_html="<p>old bio</p>", friends="old", friends_html="<p>old</p>")
	path, fields, files = case(v)
	client = as_user(v)

	with db_diff() as d:
		r = client.post(path, fields, headers=XHR, files=files)

	assert_status(r, 403)
	d.assert_exactly()


BANS = ["temporary", "permanent"]


@pytest.mark.parametrize("ban", BANS)
@pytest.mark.parametrize("name", CONTENT)
def test_suspended_users_cant_change_their_content(name, ban):
	_refused(CONTENT[name], ban)


@pytest.mark.parametrize("ban", BANS)
@pytest.mark.parametrize("name", PROFILE)
def test_suspended_users_cant_change_their_profile(name, ban):
	_refused(PROFILE[name], ban)


def test_suspended_users_can_still_delete_their_posts():
	v = _suspended()
	post = factories.post(v)
	client = as_user(v)

	with db_diff() as d:
		r = client.post(f"/delete_post/{post['id']}", headers=XHR)

	assert_status(r, 200)
	d.assert_exactly(updated={"submissions": {post["id"]: {"state_user_deleted_utc": ANY}}, "users": {v["id"]: {"post_count": 0}}})


def test_suspended_users_can_still_save_posts():
	v = _suspended()
	post = factories.post(factories.user())
	client = as_user(v)

	with db_diff() as d:
		r = client.post(f"/save_post/{post['id']}", headers=XHR)

	assert_status(r, 200)
	d.assert_exactly(inserted={"save_relationship": [{"user_id": v["id"], "submission_id": post["id"]}]})


def test_suspended_users_can_still_delete_their_comments():
	v = _suspended()
	comment = factories.comment(v, factories.post(factories.user()))
	client = as_user(v)

	with db_diff() as d:
		r = client.post(f"/delete/comment/{comment['id']}", headers=XHR)

	assert_json_message(r)
	d.assert_exactly(updated={"comments": {comment["id"]: {"state_user_deleted_utc": ANY}}, "submissions": {comment["parent_submission"]: {"comment_count": 0}}, "users": {v["id"]: {"comment_count": 0}}})


def test_suspended_users_can_still_subscribe():
	v = _suspended()
	post = factories.post(factories.user())
	client = as_user(v)

	with db_diff() as d:
		r = client.post(f"/subscribe/{post['id']}", headers=XHR)

	assert_json_message(r)
	d.assert_exactly(inserted={"subscriptions": [{"user_id": v["id"], "submission_id": post["id"]}]})


def test_suspended_users_can_still_block():
	v, other = _suspended(), factories.user()
	client = as_user(v)

	with db_diff() as d:
		r = client.post("/settings/block", {"username": other["username"]}, headers=XHR)

	assert_json_message(r)
	d.assert_exactly(inserted={"userblocks": [{"user_id": v["id"], "target_id": other["id"]}]})


@pytest.mark.parametrize("action", ["unfollow", "remove_follow"])
def test_suspended_users_can_still_end_follows(action):
	v, other = _suspended(), factories.user()
	follower, target = (v, other) if action == "unfollow" else (other, v)
	db.insert("follows", user_id=follower["id"], target_id=target["id"], created_datetimez="2024-01-01T00:00:00Z")
	db.update("users", {"id": target["id"]}, stored_subscriber_count=1)
	db.update("users", {"id": follower["id"]}, stored_following_count=1)
	client = as_user(v)

	with db_diff() as d:
		r = client.post(f"/{action}/{other['username']}", headers=XHR)

	assert_json_message(r)
	d.assert_exactly(
		inserted={"comments": [{"author_id": seed.SYSTEM_ID, "parent_submission": None}], "notifications": [{"user_id": other["id"]}]},
		updated={"users": {target["id"]: {"stored_subscriber_count": 0}, follower["id"]: {"stored_following_count": 0}}},
		deleted={"follows": [(target["id"], follower["id"])]},
	)


def test_suspended_users_can_still_change_private_preferences():
	v = _suspended(hidevotedon=False)
	client = as_user(v)

	with db_diff() as d:
		r = client.post("/settings/profile", {"hidevotedon": "true"}, headers=XHR)

	assert_status(r, 200)
	d.assert_exactly(updated={"users": {v["id"]: {"hidevotedon": True}}})


# The request also ends the ban that ran out (test_ban_expiry)
_BAN_ENDED = {"is_banned": 0, "unban_utc": 0}
_UNBANNED_NOTIFICATION = {"comments": [{"author_id": seed.SYSTEM_ID, "parent_submission": None}], "notifications": [{}]}


def test_users_whose_ban_ran_out_can_edit_their_posts():
	v = _expired()
	post = factories.post(v)
	client = as_user(v)

	with db_diff() as d:
		r = client.post(f"/edit_post/{post['id']}", {"title": post["title"], "body": "after"})

	assert_redirect(r, f"/post/{post['id']}/{post['title']}")
	d.assert_exactly(
		updated={"submissions": {post["id"]: {"body": "after", "body_html": ANY}}, "users": {v["id"]: _BAN_ENDED}},
		inserted=_UNBANNED_NOTIFICATION,
	)


def test_users_whose_ban_ran_out_can_set_their_bio():
	v = _expired()
	client = as_user(v)

	with db_diff() as d:
		r = client.post("/settings/profile", {"bio": "after"}, headers=XHR)

	assert_status(r, 200)
	d.assert_exactly(updated={"users": {v["id"]: {"bio": "after", "bio_html": ANY, **_BAN_ENDED}}}, inserted=_UNBANNED_NOTIFICATION)


def _privacy(user, private: bool) -> str:
	return f"/id/{user['id']}/private/{int(private)}"


@pytest.mark.parametrize("permanently", [False, True], ids=["temporarily", "permanently"])
def test_suspended_users_cant_change_their_profiles_privacy(permanently):
	v = _suspended(permanently)

	with db_diff() as d:
		r = as_user(v).post(_privacy(v, True), headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


def test_a_suspended_admin_cant_change_others_privacy():
	target = factories.user()
	admin = factories.admin(2, is_banned=factories.admin(3)["id"], unban_utc=int(time.time()) + 86400)

	with db_diff() as d:
		r = as_user(admin).post(_privacy(target, True), headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


def test_an_admin_whose_ban_ran_out_sets_others_privacy_again():
	admin = factories.admin(2, is_banned=factories.admin(3)["id"], unban_utc=int(time.time()) - 60)
	target = factories.user()
	client = as_user(admin)
	client.get("/")

	with db_diff() as d:
		r = client.post(_privacy(target, True), headers=XHR)

	assert_json_message(r)
	d.assert_exactly(updated={"users": {target["id"]: {"is_private": True}}})
