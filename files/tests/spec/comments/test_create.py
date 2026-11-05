'''
Commenting: POST /comment with "parent_fullname" naming what is replied to ("post_<post id>" for a top-level comment, "comment_<comment id>" for a reply) and "body" (markdown; surrounding whitespace is trimmed and it is cut to 500,000 characters).

The new comment sits one level below its parent (top-level comments are level 1) and belongs to the parent's thread (a top-level comment starts its own thread). It is 18+ when the post is, or when the request says "over_18" = "true"; it is anonymous ("ghost") when the post is. Comments from API clients are marked as bots and record the client's application. The author's own upvote comes with it.

A comment is held for review (filtered) instead of published when:
- its author's filter setting says to hold their comments, or the setting is automatic and the author falls short of any of the site settings FilterCommentsMinComments (published comments), FilterCommentsMinKarma or FilterCommentsMinAgeDays (account age). Admins of any level are never held by these;
- its body is longer than 50,000 characters, unless the author is an admin of level 3 or more.

A published comment counts toward its post's and its author's comment counts and the descendant counts of all the comments above it, and notifies, once each and never the author: users it mentions as @name (unless either has blocked the other), the post's subscribers, and the author of what it replies to (unless that author blocks the commenter). A held comment does neither.

Replies may go to deleted or removed comments and to removed posts. A draft takes comments only from those who may see it (its author and admins of level 2 or more); to anyone else it doesn't exist. Comments on a draft notify nobody while it is a draft; publishing it (POST /publish/<post id>) sends the notifications of its published comments then.

Images uploaded as "file" (up to 4; more are ignored) are stored and linked at the end of the body, and a comment of only images is allowed. Requests through Tor have their uploads dropped, so they need text.

The answer to browsers and scripts is JSON {"comment": <the comment rendered as an HTML fragment>, "message": ...} where "message" is a notice for the author when they reply to someone who blocks them (unless they're an admin of level 2 or more) or when the comment is held for its length, and null otherwise. API clients get the comment's JSON object.

Refused, changing nothing:
- 400: "parent_fullname" shorter than 4 characters or not naming a post or a comment; no body and no file (or only a file dropped for coming through Tor);
- 415: an upload that isn't an image;
- 404: an unknown post or comment, a private message, or a draft (or a comment on one) the commenter may not see;
- 409: the author already has a comment that isn't deleted with the same body under the same parent;
- 403: suspended users;
- 401: anonymous scripts (browsers are sent to log in).
'''
import os
import time

import pytest

from files.tests.spec.harness import *

DELETED = "2020-01-01T00:00:00Z"


def _on(post):
	return f"post_{post['id']}"


def _under(comment):
	return f"comment_{comment['id']}"


def _comment(client, parent_fullname, body, headers=XHR, files=None, **fields):
	return client.post("/comment", {"parent_fullname": parent_fullname, "body": body, **fields}, headers=headers, files=files)


def _row(author, post, body, parent=None, **overrides):
	'''The comment row commenting inserts.'''
	return {
		"author_id": author["id"],
		"parent_submission": post["id"],
		"parent_comment_id": parent["id"] if parent else None,
		"level": parent["level"] + 1 if parent else 1,
		"top_comment_id": parent["top_comment_id"] if parent else ANY,
		"body": body,
		"over_18": False,
		"ghost": False,
		"is_bot": False,
		"app_id": None,
		"sentto": None,
		"state_mod": "VISIBLE",
		"state_user_deleted_utc": None,
		"upvotes": 1,
		"downvotes": 0,
		"descendant_count": 0,
		"edited_utc": 0,
		"distinguish_level": 0,
		**overrides,
	}


def _vote(author):
	return {"user_id": author["id"], "comment_id": ANY, "vote_type": 1}


def _notifications(*users):
	return [{"user_id": u["id"], "comment_id": ANY, "read": False} for u in users]


def _counted(author, post, ancestors=(), author_count=1):
	'''The counter changes publishing a comment makes, from the counts as they stand now.'''
	return {
		"users": {author["id"]: {"comment_count": author_count}},
		"submissions": {post["id"]: {"comment_count": db.row("submissions", id=post["id"])["comment_count"] + 1}},
		**({"comments": {a["id"]: {"descendant_count": db.row("comments", id=a["id"])["descendant_count"] + 1} for a in ancestors}} if ancestors else {}),
	}


def _assert_answered(r, token, message=False):
	assert_status(r, 200)
	assert set(r.json) == {"comment", "message"}, r.json
	assert token in r.json["comment"]
	if message:
		assert isinstance(r.json["message"], str) and r.json["message"]
	else:
		assert r.json["message"] is None


# Placement in the thread

def test_top_level_comments_go_on_the_post():
	op, author = factories.user(), factories.user()
	post = factories.post(op)
	token = factories.unique()
	client = as_user(author)
	counted = _counted(author, post)

	with db_diff() as d:
		r = _comment(client, _on(post), token)

	_assert_answered(r, token)
	d.assert_exactly(
		inserted={"comments": [_row(author, post, token)], "commentvotes": [_vote(author)], "notifications": _notifications(op)},
		updated=counted,
	)
	new = db.row("comments", body=token)
	assert new["top_comment_id"] == new["id"]
	assert db.row("commentvotes", user_id=author["id"])["comment_id"] == new["id"]
	assert db.row("notifications", user_id=op["id"])["comment_id"] == new["id"]


def test_replies_go_one_level_below_their_parent_in_its_thread():
	op, parent_author, author = factories.user(), factories.user(), factories.user()
	post = factories.post(op)
	top = factories.comment(factories.user(), post)
	parent = factories.comment(parent_author, post, parent=top)
	token = factories.unique()
	client = as_user(author)
	counted = _counted(author, post, ancestors=[top, parent])

	with db_diff() as d:
		r = _comment(client, _under(parent), token)

	_assert_answered(r, token)
	d.assert_exactly(
		inserted={"comments": [_row(author, post, token, parent=parent, level=3, top_comment_id=top["id"])], "commentvotes": [_vote(author)], "notifications": _notifications(parent_author)},
		updated=counted,
	)


def test_the_answer_is_the_same_json_without_the_script_header():
	post = factories.post(factories.user())
	token = factories.unique()

	r = _comment(as_user(factories.user()), _on(post), token, headers=None)

	_assert_answered(r, token)


def test_a_new_comment_shows_on_its_post_and_its_permalink():
	post = factories.post(factories.user())
	token = factories.unique()
	assert_status(_comment(as_user(factories.user()), _on(post), token), 200)
	new = db.row("comments", body=token)

	assert_in_payload(anon().get(f"/post/{post['id']}"), token)
	assert_in_payload(anon().get(f"/comment/{new['id']}"), token)


def test_the_body_is_trimmed():
	post = factories.post(factories.user())
	token = factories.unique()

	assert_status(_comment(as_user(factories.user()), _on(post), f"  \n {token} \n "), 200)

	assert db.row("comments", parent_submission=post["id"])["body"] == token


def test_the_body_is_cut_to_500000_characters():
	post = factories.post(factories.user())
	body = factories.unique() + "a" * 500_000

	assert_status(_comment(as_user(factories.admin(3)), _on(post), body), 200)

	assert db.row("comments", parent_submission=post["id"])["body"] == body[:500_000]


@pytest.mark.parametrize("parent_state", [
	pytest.param({"state_user_deleted_utc": DELETED}, id="deleted"),
	pytest.param({"state_mod": "REMOVED"}, id="removed"),
])
def test_replies_to_hidden_comments_are_accepted(parent_state):
	parent_author, author = factories.user(), factories.user()
	post = factories.post(factories.user())
	parent = factories.comment(parent_author, post, **parent_state)
	token = factories.unique()
	client = as_user(author)
	counted = _counted(author, post, ancestors=[parent])

	with db_diff() as d:
		r = _comment(client, _under(parent), token)

	_assert_answered(r, token)
	d.assert_exactly(
		inserted={"comments": [_row(author, post, token, parent=parent)], "commentvotes": [_vote(author)], "notifications": _notifications(parent_author)},
		updated=counted,
	)


def test_comments_on_removed_posts_are_accepted():
	op, author = factories.user(), factories.user()
	post = factories.post(op, state_mod="REMOVED")
	token = factories.unique()
	client = as_user(author)
	counted = _counted(author, post)

	with db_diff() as d:
		r = _comment(client, _on(post), token)

	_assert_answered(r, token)
	d.assert_exactly(
		inserted={"comments": [_row(author, post, token)], "commentvotes": [_vote(author)], "notifications": _notifications(op)},
		updated=counted,
	)


# Inherited and requested flags

def test_comments_on_18_plus_posts_are_18_plus():
	post = factories.post(factories.user(), over_18=True)
	token = factories.unique()

	assert_status(_comment(as_user(factories.user()), _on(post), token), 200)

	assert db.row("comments", body=token)["over_18"] is True


@pytest.mark.parametrize("value, over_18", [("true", True), ("false", False), ("1", False)])
def test_comments_are_18_plus_when_requested_with_true(value, over_18):
	post = factories.post(factories.user())
	token = factories.unique()

	assert_status(_comment(as_user(factories.user()), _on(post), token, over_18=value), 200)

	assert db.row("comments", body=token)["over_18"] is over_18


def test_comments_on_anonymous_posts_are_anonymous():
	post = factories.post(factories.user(), ghost=True)
	token = factories.unique()

	assert_status(_comment(as_user(factories.user()), _on(post), token), 200)

	assert db.row("comments", body=token)["ghost"] is True


# API clients

def test_api_clients_comments_are_marked_as_bots_and_answered_with_the_comments_json():
	op, author = factories.user(), factories.user()
	post = factories.post(op)
	token = factories.unique()
	access_token = factories.api_token(author)
	application = db.row("client_auths", access_token=access_token)["oauth_client"]
	client = as_api(access_token)
	counted = _counted(author, post)

	with db_diff() as d:
		r = _comment(client, _on(post), token, headers=None)

	assert_status(r, 200)
	d.assert_exactly(
		inserted={"comments": [_row(author, post, token, is_bot=True, app_id=application)], "commentvotes": [_vote(author)], "notifications": _notifications(op)},
		updated=counted,
	)
	new = db.row("comments", body=token)
	# Scores are left out while the comment is younger than the score-hiding period
	assert set(r.json) == {"id", "level", "author_name", "body", "body_html", "is_bot", "created_utc", "edited_utc", "is_nsfw", "permalink", "is_pinned", "distinguish_level", "post_id", "replies", "author", "post"}
	assert {k: v for k, v in r.json.items() if k not in ("author", "post")} == {
		"id": new["id"],
		"level": 1,
		"author_name": author["username"],
		"body": token,
		"body_html": new["body_html"],
		"is_bot": True,
		"created_utc": new["created_utc"],
		"edited_utc": 0,
		"is_nsfw": False,
		"permalink": f"/comment/{new['id']}",
		"is_pinned": None,
		"distinguish_level": 0,
		"post_id": post["id"],
		"replies": [],
	}
	assert (r.json["author"]["id"], r.json["author"]["username"]) == (author["id"], author["username"])
	assert r.json["post"]["id"] == post["id"]


# Notifications

def test_mentioned_users_are_notified_once():
	author, mentioned = factories.user(), factories.user()
	post = factories.post(author)
	token = factories.unique()
	client = as_user(author)
	counted = _counted(author, post)

	with db_diff() as d:
		r = _comment(client, _on(post), f"{token} @{mentioned['username']} and again @{mentioned['username']}")

	assert_status(r, 200)
	d.assert_exactly(inserted={"comments": [{}], "commentvotes": [{}], "notifications": _notifications(mentioned)}, updated=counted)


@pytest.mark.parametrize("case", ["self", "unknown", "blocks the author", "blocked by the author"])
def test_some_mentions_notify_no_one(case):
	author, other = factories.user(), factories.user()
	post = factories.post(author)
	if case == "blocks the author":
		db.insert("userblocks", user_id=other["id"], target_id=author["id"])
	if case == "blocked by the author":
		db.insert("userblocks", user_id=author["id"], target_id=other["id"])
	name = {"self": author["username"], "unknown": factories.unique("nobody")}.get(case, other["username"])
	client = as_user(author)
	counted = _counted(author, post)

	with db_diff() as d:
		r = _comment(client, _on(post), f"{factories.unique()} @{name}")

	assert_status(r, 200)
	d.assert_exactly(inserted={"comments": [{}], "commentvotes": [{}]}, updated=counted)


def test_post_subscribers_are_notified_but_not_the_author():
	author, subscriber = factories.user(), factories.user()
	post = factories.post(author)
	blocking_subscriber = factories.user()
	db.insert("userblocks", user_id=blocking_subscriber["id"], target_id=author["id"])
	for u in (author, subscriber, blocking_subscriber):
		db.insert("subscriptions", user_id=u["id"], submission_id=post["id"])
	client = as_user(author)
	counted = _counted(author, post)

	with db_diff() as d:
		r = _comment(client, _on(post), factories.unique())

	assert_status(r, 200)
	d.assert_exactly(inserted={"comments": [{}], "commentvotes": [{}], "notifications": _notifications(subscriber, blocking_subscriber)}, updated=counted)


def test_replies_notify_the_parents_author_not_the_posts():
	op, parent_author, author = factories.user(), factories.user(), factories.user()
	post = factories.post(op)
	parent = factories.comment(parent_author, post)
	client = as_user(author)
	counted = _counted(author, post, ancestors=[parent])

	with db_diff() as d:
		r = _comment(client, _under(parent), factories.unique())

	assert_status(r, 200)
	d.assert_exactly(inserted={"comments": [{}], "commentvotes": [{}], "notifications": _notifications(parent_author)}, updated=counted)


def test_replies_to_yourself_notify_no_one():
	author = factories.user()
	post = factories.post(author)
	parent = factories.comment(author, post)
	client = as_user(author)
	counted = _counted(author, post, ancestors=[parent], author_count=2)

	with db_diff() as d:
		r = _comment(client, _under(parent), factories.unique())

	assert_status(r, 200)
	d.assert_exactly(inserted={"comments": [{}], "commentvotes": [{}]}, updated=counted)


def test_someone_notified_several_ways_is_notified_once():
	op, author = factories.user(), factories.user()
	post = factories.post(op)
	db.insert("subscriptions", user_id=op["id"], submission_id=post["id"])
	client = as_user(author)
	counted = _counted(author, post)

	with db_diff() as d:
		r = _comment(client, _on(post), f"{factories.unique()} @{op['username']}")

	assert_status(r, 200)
	d.assert_exactly(inserted={"comments": [{}], "commentvotes": [{}], "notifications": _notifications(op)}, updated=counted)


@pytest.mark.parametrize("level, message", [(0, True), (1, True), (2, False), (3, False)])
def test_replying_to_someone_who_blocks_you_doesnt_notify_them(level, message):
	parent_author, author = factories.user(), factories.admin(level)
	post = factories.post(factories.user())
	parent = factories.comment(parent_author, post)
	db.insert("userblocks", user_id=parent_author["id"], target_id=author["id"])
	token = factories.unique()
	client = as_user(author)
	counted = _counted(author, post, ancestors=[parent])

	with db_diff() as d:
		r = _comment(client, _under(parent), token)

	_assert_answered(r, token, message=message)
	d.assert_exactly(inserted={"comments": [_row(author, post, token, parent=parent)], "commentvotes": [{}]}, updated=counted)


def test_replying_to_someone_you_block_notifies_them():
	parent_author, author = factories.user(), factories.user()
	post = factories.post(factories.user())
	parent = factories.comment(parent_author, post)
	db.insert("userblocks", user_id=author["id"], target_id=parent_author["id"])
	token = factories.unique()
	client = as_user(author)
	counted = _counted(author, post, ancestors=[parent])

	with db_diff() as d:
		r = _comment(client, _under(parent), token)

	_assert_answered(r, token)
	d.assert_exactly(inserted={"comments": [{}], "commentvotes": [{}], "notifications": _notifications(parent_author)}, updated=counted)


# Held for review

def _held(author, filter_settings=None, body=None):
	'''Comments as `author` under a reply-worthy setup (a parent by someone else, a subscriber, a mention) and checks that the comment was held: inserted as filtered with the author's vote, notifying and counting nothing.'''
	for key, value in (filter_settings or {}).items():
		site_settings_set(key, value)
	post = factories.post(factories.user())
	parent = factories.comment(factories.user(), post)
	db.insert("subscriptions", user_id=factories.user()["id"], submission_id=post["id"])
	token = factories.unique()
	body = body or f"{token} @{factories.user()['username']}"
	client = as_user(author)

	with db_diff() as d:
		r = _comment(client, _under(parent), body)

	d.assert_exactly(inserted={"comments": [_row(author, post, body, parent=parent, state_mod="FILTERED")], "commentvotes": [_vote(author)]})
	return r, token


def _published(author, filter_settings=None, body=None):
	for key, value in (filter_settings or {}).items():
		site_settings_set(key, value)
	post = factories.post(factories.user())
	token = factories.unique()
	body = body or token
	client = as_user(author)

	with db_diff() as d:
		r = _comment(client, _on(post), body)

	assert_status(r, 200)
	assert db.row("comments", parent_submission=post["id"])["state_mod"] == "VISIBLE"
	return r, d


def test_comments_by_users_set_to_be_filtered_are_held():
	r, token = _held(factories.user(filter_behavior="FILTERED"))

	_assert_answered(r, token)


def _old(days):
	return int(time.time()) - days * 86400 - 60


AUTOMATIC = {
	# setting: (overrides falling short of 1, overrides meeting it)
	"FilterCommentsMinComments": ({"comment_count": 0}, {"comment_count": 1}),
	"FilterCommentsMinKarma": ({"truescore": 0}, {"truescore": 1}),
	"FilterCommentsMinAgeDays": ({}, {"created_utc": _old(1)}),
}


@pytest.mark.parametrize("setting", AUTOMATIC)
def test_automatic_filtering_holds_comments_by_users_short_of_a_threshold(setting):
	short, _ = AUTOMATIC[setting]

	r, token = _held(factories.user(filter_behavior="AUTOMATIC", **short), {setting: 1})

	_assert_answered(r, token)


@pytest.mark.parametrize("setting", AUTOMATIC)
def test_automatic_filtering_publishes_comments_by_users_meeting_the_thresholds(setting):
	_, meeting = AUTOMATIC[setting]

	_published(factories.user(filter_behavior="AUTOMATIC", **meeting), {setting: 1})


def test_unfiltered_users_are_published_whatever_the_thresholds():
	_published(factories.user(filter_behavior="UNFILTERED"), {setting: 1 for setting in AUTOMATIC})


@pytest.mark.parametrize("behavior", ["AUTOMATIC", "FILTERED"])
def test_admins_are_never_held_by_their_filter_setting(behavior):
	_published(factories.admin(1, filter_behavior=behavior), {setting: 1 for setting in AUTOMATIC})


@pytest.mark.parametrize("level", [0, 1, 2])
def test_comments_longer_than_50000_characters_are_held(level):
	token = factories.unique()

	r, _ = _held(factories.admin(level), body=token + "a" * 50_000)

	_assert_answered(r, token, message=True)


def test_head_admins_long_comments_are_published():
	token = factories.unique()

	r, _ = _published(factories.admin(3), body=token + "a" * 50_000)

	_assert_answered(r, token)


def test_comments_of_exactly_50000_characters_are_published():
	token = factories.unique()

	r, _ = _published(factories.user(), body=token + "a" * (50_000 - len(token)))

	_assert_answered(r, token)


# Uploads

def _stored_images():
	return sorted(os.listdir(config.images_dir()))


def test_uploaded_images_are_linked_after_the_text():
	post = factories.post(factories.user())
	token = factories.unique()

	r = _comment(as_user(factories.user()), _on(post), token, files={"file": uploads.png(2, 2)})

	_assert_answered(r, token)
	[name] = _stored_images()
	new = db.row("comments", parent_submission=post["id"])
	assert new["body"].startswith(f"{token}\n\n") and name in new["body"]
	assert name in new["body_html"]
	assert_serves_image(f"/images/{name}")


def test_at_most_4_images_are_kept():
	post = factories.post(factories.user())

	r = _comment(as_user(factories.user()), _on(post), factories.unique(), files={"file": [uploads.png(2, 2) for _ in range(5)]})

	assert_status(r, 200)
	names = _stored_images()
	assert len(names) == 4
	body = db.row("comments", parent_submission=post["id"])["body"]
	assert all(name in body for name in names)


def test_a_comment_of_only_an_image_is_accepted():
	post = factories.post(factories.user())

	r = _comment(as_user(factories.user()), _on(post), "", files={"file": uploads.png(2, 2)})

	assert_status(r, 200)
	[name] = _stored_images()
	assert name in db.row("comments", parent_submission=post["id"])["body"]


def test_uploads_through_tor_are_dropped_but_the_text_posted():
	post = factories.post(factories.user())
	token = factories.unique()

	r = _comment(as_user(factories.user()), _on(post), token, headers={**XHR, **TOR}, files={"file": uploads.png(2, 2)})

	_assert_answered(r, token)
	assert _stored_images() == []
	assert db.row("comments", parent_submission=post["id"])["body"] == token



def test_a_comment_of_only_an_upload_through_tor_is_refused():
	post = factories.post(factories.user())
	client = as_user(factories.user())

	with db_diff() as d:
		r = _comment(client, _on(post), "", headers={**XHR, **TOR}, files={"file": uploads.png(2, 2)})

	assert_status(r, 400)
	d.assert_exactly()
	assert _stored_images() == []


def test_uploads_that_arent_images_are_refused():
	post = factories.post(factories.user())
	client = as_user(factories.user())

	with db_diff() as d:
		r = _comment(client, _on(post), factories.unique(), files={"file": uploads.text_file()})

	assert_status(r, 415)
	d.assert_exactly()

# Refusals

def _refused(client, parent_fullname, body, status, **kwargs):
	with db_diff() as d:
		r = _comment(client, parent_fullname, body, **kwargs)

	assert_status(r, status)
	d.assert_exactly()


@pytest.mark.parametrize("parent_fullname", ["", "pos", "post", "user_1", "invalid_format", "Post_1"])
def test_parents_that_arent_posts_or_comments_are_refused(parent_fullname):
	factories.post(factories.user())

	_refused(as_user(factories.user()), parent_fullname, factories.unique(), 400)


@pytest.mark.parametrize("body", ["", "   \n "])
def test_empty_comments_are_refused(body):
	post = factories.post(factories.user())

	_refused(as_user(factories.user()), _on(post), body, 400)


def test_comments_without_a_body_field_are_refused():
	post = factories.post(factories.user())
	client = as_user(factories.user())

	with db_diff() as d:
		r = client.post("/comment", {"parent_fullname": _on(post)}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


@pytest.mark.parametrize("kind", ["post", "comment"])
@pytest.mark.parametrize("which", ["unknown", "not an id"])
def test_unknown_parents_are_not_found(kind, which):
	unknown = db.execute(f"SELECT nextval('{'submissions' if kind == 'post' else 'comments'}_id_seq')") if which == "unknown" else "abc"

	_refused(as_user(factories.user()), f"{kind}_{unknown}", factories.unique(), 404)


def test_replies_to_private_messages_are_not_found():
	sender, recipient = factories.user(), factories.user()
	message_id = db.execute("SELECT nextval('comments_id_seq')")
	body = factories.unique()
	message = db.insert("comments", id=message_id, author_id=sender["id"], sentto=recipient["id"], created_utc=int(time.time()), parent_submission=None, level=1, top_comment_id=message_id, body=body, body_html=f"<p>{body}</p>", volunteer_janitor_badness=0.5, state_mod="VISIBLE", state_report="UNREPORTED")

	_refused(as_user(recipient), _under(message), factories.unique(), 404)


@pytest.mark.parametrize("where", ["post", "reply"])
def test_comments_on_drafts_the_commenter_cant_see_are_not_found(where):
	draft = factories.post(factories.user(), private=True)
	parent_fullname = _on(draft) if where == "post" else _under(factories.comment(factories.admin(2), draft))

	_refused(as_user(factories.user()), parent_fullname, factories.unique(), 404)


@pytest.mark.parametrize("commenter", ["author", "admin"])
def test_drafts_take_comments_from_those_who_see_them(commenter):
	author = factories.user()
	draft = factories.post(author, private=True)
	v = author if commenter == "author" else factories.admin(2)
	body = factories.unique()
	client = as_user(v)
	counted = _counted(v, draft, author_count=db.row("users", id=v["id"])["comment_count"] + 1)

	with db_diff() as d:
		r = _comment(client, _on(draft), body)

	_assert_answered(r, body)
	d.assert_exactly(inserted={"comments": [_row(v, draft, body)], "commentvotes": [_vote(v)]}, updated=counted)


def test_comments_on_drafts_notify_nobody():
	author, mentioned, subscriber = factories.user(), factories.user(), factories.user()
	draft = factories.post(author, private=True)
	db.insert("subscriptions", user_id=subscriber["id"], submission_id=draft["id"])
	admin = factories.admin(2)
	parent = factories.comment(author, draft)
	body = f"hello @{mentioned['username']}"
	client = as_user(admin)
	counted = _counted(admin, draft, ancestors=[parent], author_count=db.row("users", id=admin["id"])["comment_count"] + 1)

	with db_diff() as d:
		r = _comment(client, _under(parent), body)

	_assert_answered(r, "hello")
	d.assert_exactly(inserted={"comments": [_row(admin, draft, body, parent=parent)], "commentvotes": [_vote(admin)]}, updated=counted)


def test_publishing_a_draft_sends_its_comments_notifications():
	author, mentioned, unseen = factories.user(), factories.user(), factories.user()
	draft = factories.post(author, private=True, created_utc=1000)
	admin = factories.admin(2)
	factories.comment(admin, draft, body=f"hello @{mentioned['username']}")
	factories.comment(admin, draft, body=f"deleted @{unseen['username']}", state_user_deleted_utc=DELETED)
	factories.comment(admin, draft, body=f"held @{unseen['username']}", state_mod="FILTERED")
	factories.comment(author, draft, body="the author's own")
	client = as_user(author)

	with db_diff() as d:
		r = client.post(f"/publish/{draft['id']}")

	assert_status(r, 302)
	d.assert_exactly(
		updated={"submissions": {draft["id"]: {"private": False, "created_utc": ANY}}, "users": {author["id"]: {"post_count": 1}}},
		inserted={"notifications": _notifications(mentioned, author)},
	)


def test_repeating_a_comment_you_have_twice_is_refused():
	author, post = factories.user(), factories.post(factories.user())
	body = factories.unique()
	client = as_user(author)
	assert_status(_comment(client, _on(post), body), 200)
	assert_status(_comment(client, _on(post), factories.unique()), 200)
	assert_status(client.post(f"/edit_comment/{max(r['id'] for r in db.rows('comments', author_id=author['id']))}", {"body": body}, headers=XHR), 200)

	_refused(client, _on(post), body, 409)


@pytest.mark.parametrize("where", ["post", "reply"])
def test_repeating_your_comment_under_the_same_parent_is_refused(where):
	post = factories.post(factories.user())
	parent_fullname = _on(post) if where == "post" else _under(factories.comment(factories.user(), post))
	client = as_user(factories.user())
	body = factories.unique()
	assert_status(_comment(client, parent_fullname, body), 200)

	_refused(client, parent_fullname, body, 409)


@pytest.mark.parametrize("case", ["earlier one deleted", "another post", "reply instead of top-level", "someone else's"])
def test_repeating_a_comment_is_accepted_when_not_your_live_comment_under_the_same_parent(case):
	author = factories.user()
	post = factories.post(factories.user())
	body = factories.unique()
	first_client = as_user(factories.user() if case == "someone else's" else author)
	assert_status(_comment(first_client, _on(post), body), 200)
	if case == "earlier one deleted":
		db.update("comments", {"body": body}, state_user_deleted_utc=DELETED)
	parent_fullname = {
		"another post": lambda: _on(factories.post(factories.user())),
		"reply instead of top-level": lambda: _under(factories.comment(factories.user(), post)),
	}.get(case, lambda: _on(post))()

	r = _comment(as_user(author), parent_fullname, body)

	assert_status(r, 200)
	assert len(db.rows("comments", body=body)) == 2


@pytest.mark.parametrize("ban", ["temporary", "permanent"])
def test_suspended_users_cant_comment(ban):
	v = factories.user(is_banned=factories.admin(2)["id"], unban_utc=0 if ban == "permanent" else int(time.time()) + 86400)
	post = factories.post(factories.user())

	_refused(as_user(v), _on(post), factories.unique(), 403)


def test_anonymous_scripts_are_unauthorized():
	post = factories.post(factories.user())

	with db_diff() as d:
		r = _comment(anon(), _on(post), factories.unique())

	assert_api_unauthorized(r)
	d.assert_exactly()


def test_anonymous_browsers_are_sent_to_log_in():
	post = factories.post(factories.user())

	with db_diff() as d:
		r = _comment(anon(), _on(post), factories.unique(), headers=None)

	assert_login_redirect(r, "/comment")
	d.assert_exactly()
