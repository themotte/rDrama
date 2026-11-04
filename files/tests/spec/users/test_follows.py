'''
Following users. Each action is a POST naming the other user in the path (case-insensitively, by their current or original username) and answers JSON with a "message":
- /follow/<username> makes the viewer a follower of the user. Following yourself is refused with 400; following someone already followed changes nothing. Otherwise, following a user who disabled follows ("Disable Subscriptions") or who blocks the viewer is refused with 403; following a user the viewer blocks is allowed.
- /unfollow/<username> stops the viewer following the user; doing so when not following changes nothing.
- /remove_follow/<username> stops the user following the viewer; doing so when they don't changes nothing.

Each change recounts the followed user's follower count and the follower's following count, and tells the other user, by a system message notification: a follow and an unfollow each tell the other user once per pair of users, ever (following again after unfollowing tells no one); removing a follower tells them every time. An unknown user is 404; anonymous browsers are sent to log in, and nothing changes.

GET /@<username>/followers and /@<username>/following list who follows the user and whom the user follows, oldest follow first, to anyone (logged in or not).
'''
import pytest

from files.tests.spec.harness import *

SYSTEM_MESSAGE = {"author_id": seed.SYSTEM_ID, "parent_submission": None, "level": 1, "state_mod": "VISIBLE"}


def _follow(follower, target, at="2024-01-01T00:00:00Z"):
	db.insert("follows", user_id=follower["id"], target_id=target["id"], created_datetimez=at)
	db.update("users", {"id": target["id"]}, stored_subscriber_count=len(db.rows("follows", target_id=target["id"])))
	db.update("users", {"id": follower["id"]}, stored_following_count=len(db.rows("follows", user_id=follower["id"])))


def _notice(d, user):
	'''The new notification message `user` received in diff `d`.'''
	[notification] = [n for n in d.inserted["notifications"] if n["user_id"] == user["id"]]
	[message] = [c for c in d.inserted["comments"] if c["id"] == notification["comment_id"]]
	return message


def _follow_key(follower, target):
	[row] = db.rows("follows", user_id=follower["id"], target_id=target["id"])
	return tuple(row[c] for c in ("target_id", "user_id"))


# Following

def test_following_a_user():
	follower, target = factories.user(), factories.user()

	with db_diff() as d:
		r = as_user(follower).post(f"/follow/{target['username']}")

	assert_json_message(r)
	d.assert_exactly(
		inserted={
			"follows": [{"user_id": follower["id"], "target_id": target["id"]}],
			"comments": [SYSTEM_MESSAGE],
			"notifications": [{"user_id": target["id"], "read": False}],
		},
		updated={"users": {target["id"]: {"stored_subscriber_count": 1}, follower["id"]: {"stored_following_count": 1}}},
	)
	assert follower["username"] in _notice(d, target)["body_html"]


def test_following_names_the_user_case_insensitively():
	follower, target = factories.user(), factories.user()

	r = as_user(follower).post(f"/follow/{target['username'].upper()}")

	assert_json_message(r)
	assert db.rows("follows", user_id=follower["id"], target_id=target["id"])


def test_following_counts_every_follower():
	target = factories.user()
	_follow(factories.user(), target)
	follower = factories.user()
	_follow(follower, factories.user())

	with db_diff() as d:
		as_user(follower).post(f"/follow/{target['username']}")

	d.assert_exactly(
		inserted={"follows": [{"user_id": follower["id"], "target_id": target["id"]}], "comments": [SYSTEM_MESSAGE], "notifications": [{"user_id": target["id"]}]},
		updated={"users": {target["id"]: {"stored_subscriber_count": 2}, follower["id"]: {"stored_following_count": 2}}},
	)


def test_following_again_changes_nothing():
	follower, target = factories.user(), factories.user()
	_follow(follower, target)

	with db_diff() as d:
		r = as_user(follower).post(f"/follow/{target['username']}")

	assert_json_message(r)
	d.assert_exactly()


def test_refollowing_after_unfollowing_tells_no_one():
	follower, target = factories.user(), factories.user()
	client = as_user(follower)
	client.post(f"/follow/{target['username']}")
	client.post(f"/unfollow/{target['username']}")

	with db_diff() as d:
		r = client.post(f"/follow/{target['username']}")

	assert_json_message(r)
	d.assert_exactly(
		inserted={"follows": [{"user_id": follower["id"], "target_id": target["id"]}]},
		updated={"users": {target["id"]: {"stored_subscriber_count": 1}, follower["id"]: {"stored_following_count": 1}}},
	)


def test_following_yourself_is_refused():
	user = factories.user()

	with db_diff() as d:
		r = as_user(user).post(f"/follow/{user['username']}")

	assert_status(r, 400)
	d.assert_exactly()


def test_following_a_user_who_disabled_follows_is_refused():
	follower, target = factories.user(), factories.user(is_nofollow=True)

	with db_diff() as d:
		r = as_user(follower).post(f"/follow/{target['username']}", headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


def test_an_existing_follow_survives_the_user_disabling_follows():
	follower, target = factories.user(), factories.user()
	_follow(follower, target)
	db.update("users", {"id": target["id"]}, is_nofollow=True)

	with db_diff() as d:
		r = as_user(follower).post(f"/follow/{target['username']}")

	assert_json_message(r)
	d.assert_exactly()


@pytest.mark.parametrize("mutual", [False, True], ids=["one way", "mutual"])
def test_following_a_user_who_blocks_you_is_refused(mutual):
	follower, target = factories.user(), factories.user()
	db.insert("userblocks", user_id=target["id"], target_id=follower["id"])
	if mutual:
		db.insert("userblocks", user_id=follower["id"], target_id=target["id"])

	with db_diff() as d:
		r = as_user(follower).post(f"/follow/{target['username']}", headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


def test_following_a_user_you_block_is_allowed():
	follower, target = factories.user(), factories.user()
	db.insert("userblocks", user_id=follower["id"], target_id=target["id"])

	with db_diff() as d:
		r = as_user(follower).post(f"/follow/{target['username']}")

	assert_json_message(r)
	d.assert_exactly(
		inserted={"follows": [{"user_id": follower["id"], "target_id": target["id"]}], "comments": [SYSTEM_MESSAGE], "notifications": [{"user_id": target["id"]}]},
		updated={"users": {target["id"]: {"stored_subscriber_count": 1}, follower["id"]: {"stored_following_count": 1}}},
	)


@pytest.mark.parametrize("action", ["/follow", "/unfollow", "/remove_follow"])
def test_follow_actions_on_an_unknown_user_are_not_found(action):
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.post(f"{action}/{factories.unique()}")

	assert_status(r, 404)
	d.assert_exactly()


@pytest.mark.parametrize("action", ["/follow", "/unfollow", "/remove_follow"])
def test_follow_actions_send_anonymous_browsers_to_log_in(action):
	path = f"{action}/{factories.user()['username']}"

	with db_diff() as d:
		r = anon().post(path)

	assert_login_redirect(r, path)
	d.assert_exactly()


# Unfollowing

def test_unfollowing_a_user():
	follower, target = factories.user(), factories.user()
	_follow(follower, target)
	key = _follow_key(follower, target)

	with db_diff() as d:
		r = as_user(follower).post(f"/unfollow/{target['username']}")

	assert_json_message(r)
	d.assert_exactly(
		inserted={"comments": [SYSTEM_MESSAGE], "notifications": [{"user_id": target["id"], "read": False}]},
		updated={"users": {target["id"]: {"stored_subscriber_count": 0}, follower["id"]: {"stored_following_count": 0}}},
		deleted={"follows": [key]},
	)
	assert follower["username"] in _notice(d, target)["body_html"]


def test_unfollowing_twice_over_tells_once():
	follower, target = factories.user(), factories.user()
	client = as_user(follower)
	client.post(f"/follow/{target['username']}")
	client.post(f"/unfollow/{target['username']}")
	client.post(f"/follow/{target['username']}")
	key = _follow_key(follower, target)

	with db_diff() as d:
		r = client.post(f"/unfollow/{target['username']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"users": {target["id"]: {"stored_subscriber_count": 0}, follower["id"]: {"stored_following_count": 0}}},
		deleted={"follows": [key]},
	)


def test_unfollowing_someone_not_followed_changes_nothing():
	follower, target = factories.user(), factories.user()
	_follow(target, follower)

	with db_diff() as d:
		r = as_user(follower).post(f"/unfollow/{target['username']}")

	assert_json_message(r)
	d.assert_exactly()


# Removing a follower

def test_removing_a_follower():
	user, follower = factories.user(), factories.user()
	_follow(follower, user)
	key = _follow_key(follower, user)

	with db_diff() as d:
		r = as_user(user).post(f"/remove_follow/{follower['username']}")

	assert_json_message(r)
	d.assert_exactly(
		inserted={"comments": [SYSTEM_MESSAGE], "notifications": [{"user_id": follower["id"], "read": False}]},
		updated={"users": {user["id"]: {"stored_subscriber_count": 0}, follower["id"]: {"stored_following_count": 0}}},
		deleted={"follows": [key]},
	)
	assert user["username"] in _notice(d, follower)["body_html"]


def test_removing_a_follower_again_tells_them_again():
	user, follower = factories.user(), factories.user()
	_follow(follower, user)
	as_user(user).post(f"/remove_follow/{follower['username']}")
	_follow(follower, user)
	key = _follow_key(follower, user)

	with db_diff() as d:
		r = as_user(user).post(f"/remove_follow/{follower['username']}")

	assert_json_message(r)
	d.assert_exactly(
		inserted={"comments": [SYSTEM_MESSAGE], "notifications": [{"user_id": follower["id"]}]},
		updated={"users": {user["id"]: {"stored_subscriber_count": 0}, follower["id"]: {"stored_following_count": 0}}},
		deleted={"follows": [key]},
	)


def test_removing_someone_who_doesnt_follow_changes_nothing():
	user, other = factories.user(), factories.user()
	_follow(user, other)

	with db_diff() as d:
		r = as_user(user).post(f"/remove_follow/{other['username']}")

	assert_json_message(r)
	d.assert_exactly()


# The lists

LISTS = {
	"followers": lambda user, other, at: _follow(other, user, at),
	"following": lambda user, other, at: _follow(user, other, at),
}


@pytest.mark.parametrize("listing", LISTS)
@pytest.mark.parametrize("viewer", ["anonymous", "user"])
def test_follow_lists_show_the_follows(listing, viewer):
	user, listed, unrelated = factories.user(), factories.user(), factories.user()
	LISTS[listing](user, listed, "2024-01-01T00:00:00Z")
	LISTS[listing](unrelated, factories.user(), "2024-01-01T00:00:00Z")
	client = anon() if viewer == "anonymous" else as_user(factories.user())

	r = client.get(f"/@{user['username']}/{listing}")

	assert_html(r, 200)
	assert_in_payload(r, listed["username"])
	assert_not_in_payload(r, unrelated["username"])


@pytest.mark.parametrize("listing", LISTS)
def test_follow_lists_show_the_other_direction_apart(listing):
	user, other = factories.user(), factories.user()
	other_listing = "following" if listing == "followers" else "followers"
	LISTS[other_listing](user, other, "2024-01-01T00:00:00Z")

	r = anon().get(f"/@{user['username']}/{listing}")

	assert_html(r, 200)
	assert_not_in_payload(r, other["username"])


@pytest.mark.parametrize("listing", LISTS)
def test_follow_lists_show_the_oldest_follow_first(listing):
	user, newer, older = factories.user(), factories.user(), factories.user()
	LISTS[listing](user, newer, "2024-02-01T00:00:00Z")
	LISTS[listing](user, older, "2024-01-01T00:00:00Z")

	r = anon().get(f"/@{user['username']}/{listing}")

	assert_html(r, 200)
	assert r.text.index(older["username"]) < r.text.index(newer["username"])


@pytest.mark.parametrize("listing", LISTS)
def test_follow_lists_of_an_unknown_user_are_not_found(listing):
	r = anon().get(f"/@{factories.unique()}/{listing}")

	assert_status(r, 404)
