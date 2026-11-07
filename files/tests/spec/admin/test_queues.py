'''
The moderation queues, admin pages listing posts or comments 25 to a page, newest first, with "page" (from 1) choosing the page:
- GET /admin/filtered/posts and /admin/filtered/comments: items held for moderator approval.
- GET /admin/reported/posts and /admin/reported/comments: items with an open report.
- GET /admin/removed/posts and /admin/removed/comments: items a moderator removed, and every item by a shadowbanned author.
- GET /admin/image_posts: posts whose link is an image: the URL ends (case-insensitively) in .webp, .jpg, .jpeg, .png or .gif, or in "?maxwidth=9999" or "&fidelity=high", and points at the site itself (a path, or the site's own URL) or at an approved embedding host over https.

The queues show 18+ items whole, whether or not the admin confirmed their age.

POST /admin/update_filter_status settles one item from a queue. Its JSON body names the item ("post_id" or "comment_id") and a "new_status": "normal" makes it visible, "removed" removes it, both resolving its reports; "ignored" only marks its reports ignored. Changing whether others can see the item is logged in the mod log and has the item's usual effects (approving a held post notifies the users it mentions and the author's followers). The reply is JSON whose "result" the page script compares against "Update successful". A body that isn't a JSON object, an unknown "new_status" or an item id that isn't a whole number (a JSON integer or a string of digits) is refused with 400; a missing or unknown item is 404. An invalid "page" (not a number, or below 1) shows the first page.
'''
import pytest

from files.tests.spec.harness import *

SHADOWBANNED = "shadowbanned"
'''Marks an item whose author is shadowbanned (otherwise the item is in the given state, by an ordinary author).'''

QUEUES = {
	"/admin/filtered/posts": ([{"state_mod": "FILTERED"}], [{}, {"state_mod": "REMOVED"}, {"state_report": "REPORTED"}]),
	"/admin/reported/posts": ([{"state_report": "REPORTED"}], [{}, {"state_report": "RESOLVED"}, {"state_report": "IGNORED"}, {"state_mod": "FILTERED"}]),
	"/admin/removed/posts": ([{"state_mod": "REMOVED"}, SHADOWBANNED], [{}, {"state_mod": "FILTERED"}, {"state_report": "REPORTED"}]),
	"/admin/filtered/comments": ([{"state_mod": "FILTERED"}], [{}, {"state_mod": "REMOVED"}, {"state_report": "REPORTED"}]),
	"/admin/reported/comments": ([{"state_report": "REPORTED"}], [{}, {"state_report": "RESOLVED"}, {"state_report": "IGNORED"}, {"state_mod": "FILTERED"}]),
	"/admin/removed/comments": ([{"state_mod": "REMOVED"}, SHADOWBANNED], [{}, {"state_mod": "FILTERED"}, {"state_report": "REPORTED"}]),
}


def _item(queue, state, post=None):
	'''An item of the queue's kind in `state`, returning the sentinel its listing shows.'''
	token = factories.unique()
	author = factories.user(shadowbanned="somemod") if state == SHADOWBANNED else factories.user()
	overrides = {} if state == SHADOWBANNED else state
	if queue.endswith("/posts"):
		factories.post(author, title=token, **overrides)
	else:
		factories.comment(author, post or factories.post(factories.user()), body=token, **overrides)
	return token


def _membership_cases(listed: bool):
	return [pytest.param(queue, state, id=f"{queue} {state}") for queue, (ins, outs) in QUEUES.items() for state in (ins if listed else outs)]


@pytest.mark.parametrize("queue, state", _membership_cases(listed=True))
def test_queue_lists_its_items(queue, state):
	token = _item(queue, state)

	r = as_user(factories.admin(2)).get(queue)

	assert_html(r, 200)
	assert_in_payload(r, token)


@pytest.mark.parametrize("queue, state", _membership_cases(listed=False))
def test_queue_omits_other_items(queue, state):
	listed = _item(queue, QUEUES[queue][0][0])
	token = _item(queue, state)

	r = as_user(factories.admin(2)).get(queue)

	assert_html(r, 200)
	assert_in_payload(r, listed)
	assert_not_in_payload(r, token)


@pytest.mark.parametrize("queue", QUEUES)
def test_queues_show_18_plus_items_whole_to_admins_who_have_not_confirmed_their_age(queue):
	state = QUEUES[queue][0][0]
	overrides = {} if state == SHADOWBANNED else state
	author = factories.user(shadowbanned="somemod") if state == SHADOWBANNED else factories.user()
	text = factories.unique()
	if queue.endswith("/posts"):
		factories.post(author, body=text, over_18=True, **overrides)
	else:
		factories.comment(author, factories.post(factories.user(), over_18=True), body=text, **overrides)

	r = as_user(factories.admin(2, over_18=False)).get(queue)

	assert_html(r, 200)
	assert_in_payload(r, text)


@pytest.mark.parametrize("queue", QUEUES)
def test_queue_lists_newest_first(queue):
	older = _item(queue, QUEUES[queue][0][0])
	newer = _item(queue, QUEUES[queue][0][0])

	r = as_user(factories.admin(2)).get(queue)

	assert_html(r, 200)
	assert r.text.index(newer) < r.text.index(older)


@pytest.mark.parametrize("queue", QUEUES)
@pytest.mark.parametrize("page", [1, 2])
def test_queue_pages_hold_25_items(queue, page):
	post = factories.post(factories.user())
	oldest, *rest = [_item(queue, QUEUES[queue][0][0], post) for _ in range(26)]

	r = as_user(factories.admin(2)).get(queue, params={"page": page})

	assert_html(r, 200)
	on_page, off_page = (rest, [oldest]) if page == 1 else ([oldest], rest)
	for token in on_page:
		assert_in_payload(r, token)
	for token in off_page:
		assert_not_in_payload(r, token)


# The image feed

IMAGE_URLS = [
	"/images/a.webp",
	"/images/a.jpg",
	"/images/a.jpeg",
	"/images/a.png",
	"/images/a.gif",
	"/images/a.PNG",
	"/images/a.JpEg",
	"SITE/images/a.png",
	"https://i.imgur.com/a.jpg",
	"https://imgur.com/a.gif",
	"https://i.imgur.com/a?maxwidth=9999",
	"https://i.imgur.com/a?x=1&fidelity=high",
	"https://i.imgur.com/a?x=1&FIDELITY=HIGH",
]

NOT_IMAGE_URLS = [
	None,
	"/images/a.mp4",
	"/images/a.png?x=1",
	"/images/apng",
	"https://example.com/a.png",
	"http://i.imgur.com/a.png",
	"https://evilimgur.com/a.png",
	"https://imgur.com.example.com/a.png",
	"https://i.imgur.com/a!b.png",
	"SITE.example.com/a.png",
	"https://example.com/a?maxwidth=9999",
	"https://i.imgur.com/a?maxwidth=999",
	"https://i.imgur.com/a?fidelity=high",
]


def _image_post(url):
	token = factories.unique()
	factories.post(factories.user(), title=token, url=url.replace("SITE", config.site_url()) if url else None)
	return token


@pytest.mark.parametrize("url", IMAGE_URLS)
def test_image_feed_lists_image_posts(url):
	token = _image_post(url)

	r = as_user(factories.admin(2)).get("/admin/image_posts")

	assert_html(r, 200)
	assert_in_payload(r, token)


@pytest.mark.parametrize("url", NOT_IMAGE_URLS)
def test_image_feed_omits_other_posts(url):
	listed = _image_post("/images/a.png")
	token = _image_post(url)

	r = as_user(factories.admin(2)).get("/admin/image_posts")

	assert_html(r, 200)
	assert_in_payload(r, listed)
	assert_not_in_payload(r, token)


def test_image_feed_lists_newest_first():
	older, newer = _image_post("/images/a.png"), _image_post("/images/b.png")

	r = as_user(factories.admin(2)).get("/admin/image_posts")

	assert_html(r, 200)
	assert r.text.index(newer) < r.text.index(older)


@pytest.mark.parametrize("page", [1, 2])
def test_image_feed_pages_hold_25_image_posts(page):
	oldest = _image_post("/images/a.png")
	rest = []
	for _ in range(25):
		_image_post(None)
		rest.append(_image_post("/images/a.png"))

	r = as_user(factories.admin(2)).get("/admin/image_posts", params={"page": page})

	assert_html(r, 200)
	on_page, off_page = (rest, [oldest]) if page == 1 else ([oldest], rest)
	for token in on_page:
		assert_in_payload(r, token)
	for token in off_page:
		assert_not_in_payload(r, token)


# Settling posts

def _settle(admin, new_status, **item):
	return as_user(admin).post_json("/admin/update_filter_status", {"new_status": new_status, **item})


def _assert_settled(r):
	assert_status(r, 200)
	assert r.json == {"result": "Update successful"}, r.json


def _assert_not_found(r):
	assert_status(r, 404)
	assert set(r.json) == {"result"}, r.json


def test_approving_a_held_post_publishes_it():
	author = factories.user()
	post = factories.post(author, state_mod="FILTERED", state_report="REPORTED")
	admin = factories.admin(2)

	with db_diff() as d:
		r = _settle(admin, "normal", post_id=post["id"])

	_assert_settled(r)
	d.assert_exactly(
		updated={
			"submissions": {post["id"]: {"state_mod": "VISIBLE", "state_mod_set_by": admin["username"], "state_report": "RESOLVED"}},
			"users": {author["id"]: {"post_count": 1}},
		},
		inserted={"modactions": [{"kind": "approve_post", "user_id": admin["id"], "target_submission_id": post["id"], "target_comment_id": None}]},
	)


def test_approving_a_held_post_notifies_mentioned_users_and_followers():
	mentioned, follower = factories.user(), factories.user()
	author = factories.user()
	db.insert("follows", user_id=follower["id"], target_id=author["id"])
	post = factories.post(author, state_mod="FILTERED", body=f"hello @{mentioned['username']}")
	admin = factories.admin(2)

	with db_diff() as d:
		r = _settle(admin, "normal", post_id=post["id"])

	_assert_settled(r)
	d.assert_exactly(
		updated={
			"submissions": {post["id"]: {"state_mod": "VISIBLE", "state_mod_set_by": admin["username"], "state_report": "RESOLVED"}},
			"users": {author["id"]: {"post_count": 1}},
		},
		inserted={
			"modactions": [{"kind": "approve_post", "user_id": admin["id"], "target_submission_id": post["id"]}],
			"comments": [{"author_id": seed.SYSTEM_ID, "parent_submission": None}, {"author_id": seed.AUTOJANNY_ID, "parent_submission": None}],
			"notifications": [{"user_id": mentioned["id"]}, {"user_id": follower["id"]}],
		},
	)


def test_removing_a_visible_post_hides_it():
	author = factories.user()
	post = factories.post(author, state_report="REPORTED")
	admin = factories.admin(2)

	with db_diff() as d:
		r = _settle(admin, "removed", post_id=post["id"])

	_assert_settled(r)
	d.assert_exactly(
		updated={
			"submissions": {post["id"]: {"state_mod": "REMOVED", "state_mod_set_by": admin["username"], "state_report": "RESOLVED"}},
			"users": {author["id"]: {"post_count": 0}},
		},
		inserted={"modactions": [{"kind": "remove_post", "user_id": admin["id"], "target_submission_id": post["id"], "target_comment_id": None}]},
	)


def test_removing_a_held_post_logs_nothing():
	post = factories.post(factories.user(), state_mod="FILTERED")
	admin = factories.admin(2)

	with db_diff() as d:
		r = _settle(admin, "removed", post_id=post["id"])

	_assert_settled(r)
	d.assert_exactly(updated={"submissions": {post["id"]: {"state_mod": "REMOVED", "state_mod_set_by": admin["username"], "state_report": "RESOLVED"}}})


@pytest.mark.parametrize("new_status, state", [("normal", "VISIBLE"), ("removed", "REMOVED")])
def test_settling_a_post_into_the_state_it_has_only_resolves_reports(new_status, state):
	post = factories.post(factories.user(), state_mod=state, state_report="REPORTED")
	admin = factories.admin(2)

	with db_diff() as d:
		r = _settle(admin, new_status, post_id=post["id"])

	_assert_settled(r)
	d.assert_exactly(updated={"submissions": {post["id"]: {"state_mod_set_by": admin["username"], "state_report": "RESOLVED"}}})


@pytest.mark.parametrize("state", ["VISIBLE", "FILTERED", "REMOVED"])
def test_ignoring_a_post_only_marks_its_reports_ignored(state):
	post = factories.post(factories.user(), state_mod=state, state_report="REPORTED")
	admin = factories.admin(2)

	with db_diff() as d:
		r = _settle(admin, "ignored", post_id=post["id"])

	_assert_settled(r)
	d.assert_exactly(updated={"submissions": {post["id"]: {"state_report": "IGNORED"}}})


# Settling comments

def test_approving_a_held_reply_publishes_it():
	post = factories.post(factories.user())
	parent = factories.comment(factories.user(), post)
	author = factories.user()
	reply = factories.comment(author, post, parent, state_mod="FILTERED", state_report="REPORTED")
	admin = factories.admin(2)

	with db_diff() as d:
		r = _settle(admin, "normal", comment_id=reply["id"])

	_assert_settled(r)
	d.assert_exactly(
		updated={
			"comments": {reply["id"]: {"state_mod": "VISIBLE", "state_mod_set_by": admin["username"], "state_report": "RESOLVED"}, parent["id"]: {"descendant_count": 1}},
			"submissions": {post["id"]: {"comment_count": 2}},
			"users": {author["id"]: {"comment_count": 1}},
		},
		inserted={
			"modactions": [{"kind": "approve_comment", "user_id": admin["id"], "target_comment_id": reply["id"], "target_submission_id": None}],
			"notifications": [{"user_id": parent["author_id"], "comment_id": reply["id"]}],
		},
	)


def test_removing_a_visible_reply_hides_it():
	post = factories.post(factories.user())
	parent = factories.comment(factories.user(), post)
	author = factories.user()
	reply = factories.comment(author, post, parent, state_report="REPORTED")
	admin = factories.admin(2)

	with db_diff() as d:
		r = _settle(admin, "removed", comment_id=reply["id"])

	_assert_settled(r)
	d.assert_exactly(
		updated={
			"comments": {reply["id"]: {"state_mod": "REMOVED", "state_mod_set_by": admin["username"], "state_report": "RESOLVED"}, parent["id"]: {"descendant_count": 0}},
			"submissions": {post["id"]: {"comment_count": 1}},
			"users": {author["id"]: {"comment_count": 0}},
		},
		inserted={"modactions": [{"kind": "remove_comment", "user_id": admin["id"], "target_comment_id": reply["id"], "target_submission_id": None}]},
	)


@pytest.mark.parametrize("state", ["VISIBLE", "FILTERED", "REMOVED"])
def test_ignoring_a_comment_only_marks_its_reports_ignored(state):
	comment = factories.comment(factories.user(), factories.post(factories.user()), state_mod=state, state_report="REPORTED")
	admin = factories.admin(2)

	with db_diff() as d:
		r = _settle(admin, "ignored", comment_id=comment["id"])

	_assert_settled(r)
	d.assert_exactly(updated={"comments": {comment["id"]: {"state_report": "IGNORED"}}})


def _message(author, recipient):
	return factories.message(author, recipient, created_utc=1000, state_report="REPORTED")


def test_removing_a_private_message_hides_it_without_touching_counts():
	message = _message(factories.user(), factories.user())
	admin = factories.admin(2)

	with db_diff() as d:
		r = _settle(admin, "removed", comment_id=message["id"])

	_assert_settled(r)
	d.assert_exactly(
		updated={"comments": {message["id"]: {"state_mod": "REMOVED", "state_mod_set_by": admin["username"], "state_report": "RESOLVED"}}},
		inserted={"modactions": [{"kind": "remove_comment", "user_id": admin["id"], "target_comment_id": message["id"]}]},
	)


# Settling nothing

def test_settling_without_an_item_is_not_found():
	admin = factories.admin(2)

	with db_diff() as d:
		r = _settle(admin, "normal")

	_assert_not_found(r)
	d.assert_exactly()


def test_settling_an_unknown_post_is_not_found():
	post = factories.post(factories.user())
	db.delete("votes", submission_id=post["id"])
	db.delete("submissions", id=post["id"])
	admin = factories.admin(2)

	with db_diff() as d:
		r = _settle(admin, "normal", post_id=post["id"])

	_assert_not_found(r)
	d.assert_exactly()


def test_settling_an_unknown_comment_is_not_found():
	comment = factories.comment(factories.user(), factories.post(factories.user()))
	db.delete("commentvotes", comment_id=comment["id"])
	db.delete("comments", id=comment["id"])
	admin = factories.admin(2)

	with db_diff() as d:
		r = _settle(admin, "normal", comment_id=comment["id"])

	_assert_not_found(r)
	d.assert_exactly()


@pytest.mark.parametrize("body", [
	pytest.param({"new_status": "approved", "post_id": "{post}"}, id="unknown status"),
	pytest.param({"new_status": "normal", "post_id": "first"}, id="post id not a number"),
	pytest.param({"new_status": "normal", "comment_id": [1]}, id="comment id not a number"),
	pytest.param({"new_status": "normal", "post_id": "{post}.9"}, id="post id with a fraction"),
	pytest.param({"new_status": "normal", "post_id": 0.5}, id="post id a JSON fraction"),
	pytest.param({"new_status": "normal", "post_id": True}, id="post id a boolean"),
	pytest.param({"new_status": "normal", "post_id": " {post}"}, id="post id with a space"),
])
def test_a_malformed_settlement_is_refused(body):
	post = factories.post(factories.user(), state_mod="FILTERED")
	client = as_user(factories.admin(2))
	body = {k: (v.replace("{post}", str(post["id"])) if isinstance(v, str) else post["id"] + v if isinstance(v, float) else v) for k, v in body.items()}

	with db_diff() as d:
		r = client.post_json("/admin/update_filter_status", body, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


def test_a_settlement_that_is_not_json_is_refused():
	post = factories.post(factories.user(), state_mod="FILTERED")
	client = as_user(factories.admin(2))

	with db_diff() as d:
		r = client.post("/admin/update_filter_status", {"new_status": "normal", "post_id": post["id"]}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


LISTINGS = [*QUEUES, "/admin/image_posts", "/admin/users"]


@pytest.mark.parametrize("path", LISTINGS)
@pytest.mark.parametrize("page", ["0", "-1", "first"])
def test_an_invalid_page_shows_the_first(path, page):
	if path in QUEUES: token = _item(path, QUEUES[path][0][0])
	elif path == "/admin/image_posts": token = _image_post("/images/first.png")
	else: token = factories.user()["username"]
	client = as_user(factories.admin(2))

	r = client.get(path, params={"page": page})

	assert_html(r, 200)
	assert_in_payload(r, token)
