'''
Submitting a post: GET /submit (the form) and POST /submit.

Fields: "title" (required, at most 500 characters), "url" (at most 2048) and/or "body" (at most 500000), "private" (any non-empty value makes the post a draft), "over_18" (any non-empty value marks it 18+), "file" (an image to post instead of a link) and "file2" (up to four images linked at the end of the body).

Browsers get the new post's page; API clients get its JSON. Refusals render the form again with status 400, or for scripts and API clients a JSON error.
'''
import json
import re
from urllib.parse import parse_qs, urlsplit

import pytest

from files.tests.spec.harness import *


def _submit(client, headers=None, files=None, **fields):
	return client.post("/submit", fields, headers=headers, files=files)


def _text_post(**fields):
	return {"title": factories.unique("title"), "body": factories.unique("body"), **fields}


# The form

def test_users_get_the_form():
	assert_html(as_user(factories.user()).get("/submit"), 200)


def test_visitors_are_sent_to_log_in():
	assert_login_redirect(anon().get("/submit"), "/submit")


def test_unknown_api_tokens_are_unauthorized():
	assert_api_unauthorized(as_api("not-a-real-token").get("/submit"))


def test_an_unknown_api_token_overrides_a_logged_in_session():
	client = as_user(factories.user())
	client.authorization = "not-a-real-token"

	assert_api_unauthorized(client.get("/submit"))


# Text and link posts

def test_text_post():
	author = factories.user()
	fields = _text_post()

	with db_diff() as d:
		r = _submit(as_user(author), **fields)

	assert_html(r, 200)
	assert_in_payload(r, fields["title"])
	assert_in_payload(r, fields["body"])
	d.assert_exactly(
		inserted={
			"submissions": [{
				"author_id": author["id"], "title": fields["title"], "title_html": fields["title"], "body": fields["body"], "body_html": f"<p>{fields['body']}</p>\n", "url": None,
				"private": False, "over_18": False, "is_bot": False, "app_id": None, "ghost": False, "state_mod": "VISIBLE", "state_report": "UNREPORTED",
				"upvotes": 1, "downvotes": 0, "realupvotes": 1, "views": 0, "comment_count": 0, "embed_url": None, "thumburl": None, "edited_utc": 0,
			}],
			"votes": [{"user_id": author["id"], "vote_type": 1, "real": True, "app_id": None}],
		},
		updated={"users": {author["id"]: {"post_count": 1}}},
	)


def test_link_post():
	author = factories.user()
	url = f"https://example.com/{factories.unique('page')}"

	with db_diff() as d:
		r = _submit(as_user(author), title=factories.unique("title"), url=url)

	assert_html(r, 200)
	d.assert_exactly(
		inserted={"submissions": [{"url": url, "body": "", "body_html": "", "thumburl": None}], "votes": [{"user_id": author["id"]}]},
		updated={"users": {author["id"]: {"post_count": 1}}},
	)


def test_draft():
	author = factories.user()

	with db_diff() as d:
		_submit(as_user(author), **_text_post(private="1"))

	d.assert_exactly(inserted={"submissions": [{"private": True}], "votes": [{"user_id": author["id"]}]})


@pytest.mark.parametrize("value", ["true", "false", "0"])
def test_any_non_empty_18_plus_value_marks_the_post_18_plus(value):
	assert_html(_submit(as_user(factories.user()), **_text_post(over_18=value)), 200)

	assert db.rows("submissions")[-1]["over_18"] is True


def test_empty_18_plus_value_leaves_the_post_unmarked():
	assert_html(_submit(as_user(factories.user()), **_text_post(over_18="")), 200)

	assert db.rows("submissions")[-1]["over_18"] is False


def test_zero_width_characters_and_surrounding_space_are_stripped():
	assert_html(_submit(as_user(factories.user()), title=" a\u200bb\u200ec\ufeff ", body=" x\u200by\r\nz ", url=" https://example.com/\u200epage "), 200)

	post = db.rows("submissions")[-1]
	assert (post["title"], post["body"], post["url"]) == ("abc", "xy\nz", "https://example.com/page")


def test_api_clients_get_the_new_post_as_json():
	author = factories.user()
	token = factories.api_token(author)
	fields = _text_post()

	with db_diff() as d:
		r = _submit(as_api(token), **fields)

	assert_status(r, 200)
	app_id = db.row("client_auths", access_token=token)["oauth_client"]
	d.assert_exactly(
		inserted={"submissions": [{"is_bot": True, "app_id": app_id}], "votes": [{"user_id": author["id"]}]},
		updated={"users": {author["id"]: {"post_count": 1}}},
	)
	post = db.rows("submissions")[-1]
	assert (r.json["id"], r.json["title"], r.json["is_bot"]) == (post["id"], fields["title"], True)


# Refusals

def test_visitors_cannot_submit():
	with db_diff() as d:
		r = _submit(anon(), headers=XHR, **_text_post())

	assert_api_unauthorized(r)
	d.assert_exactly()


@pytest.mark.parametrize("fields", [
	{"body": "x"},
	{"title": "", "body": "x"},
	{"title": "   ", "body": "x"},
	{"title": "t" * 501, "body": "x"},
	{"title": "t", "url": "https://example.com/" + "a" * 2029},
	{"title": "t", "body": "b" * 500001},
], ids=["no title", "empty title", "blank title", "long title", "long url", "long body"])
def test_out_of_bounds_fields_are_refused(fields):
	client = as_user(factories.user())

	with db_diff() as d:
		r = _submit(client, headers=XHR, **fields)

	assert_status(r, 400)
	assert set(r.json) == {"code", "description", "details", "error"}
	d.assert_exactly()


@pytest.mark.parametrize("fields", [
	{"title": "\u200e\u200e\u200e", "body": "x"},
	{"title": "\u200b", "body": "x"},
	{"title": "\u200f", "body": "x"},
	{"title": "\u200f \u200f", "body": "x"},
	{"title": "t", "body": "\u200e\u200b\ufeff"},
], ids=["title of left-to-right marks", "title of zero-width spaces", "title of right-to-left marks", "title of marks and spaces", "body"])
def test_text_of_only_invisible_characters_counts_as_empty(fields):
	client = as_user(factories.user())

	with db_diff() as d:
		r = _submit(client, headers=XHR, **fields)

	assert_status(r, 400)
	d.assert_exactly()


def test_requests_over_8_megabytes_are_refused():
	client = as_user(factories.user())

	with db_diff() as d:
		r = _submit(client, headers=XHR, title="t", body="b" * (9 * 1024 * 1024))

	assert_status(r, 413)
	d.assert_exactly()


def test_fields_at_their_limits_are_accepted():
	assert_html(_submit(as_user(factories.user()), title="t" * 500, url="https://example.com/" + "a" * 2028, body="b" * 500000), 200)

	post = db.rows("submissions")[-1]
	assert (len(post["title"]), len(post["url"]), len(post["body"])) == (500, 2048, 500000)


def test_long_bodies_of_non_ascii_text_are_accepted():
	assert_html(_submit(as_user(factories.user()), title="t", body="é" * 400000), 200)

	assert len(db.rows("submissions")[-1]["body"]) == 400000


@pytest.mark.parametrize("url", ["javascript:alert(1)", "example.com/page", "//example.com/page", "ftp://example.com/file", "data:text/html,hi", "http://[", "https://", "https://someone@/page", "https://:80/page", "https://evil.example\\@good.example/page"])
def test_links_must_be_web_addresses(url):
	client = as_user(factories.user())

	with db_diff() as d:
		r = _submit(client, headers=XHR, title="t", url=url)

	assert_status(r, 400)
	d.assert_exactly()


def test_link_schemes_are_case_insensitive():
	assert_html(_submit(as_user(factories.user()), title="t", url="HTTPS://example.com/page"), 200)


def test_a_post_needs_a_link_text_or_image():
	client = as_user(factories.user())

	with db_diff() as d:
		r = _submit(client, title=factories.unique("title"))

	assert_html(r, 400)
	d.assert_exactly()


@pytest.mark.parametrize("fields", [{"body": "", "url": ""}, {"url": "https://example.com/" + "a" * 2029}, {"url": "ftp://example.com/x"}], ids=["no content", "long link", "not a web link"])
def test_the_refused_form_keeps_the_title(fields):
	title = factories.unique("title")

	r = _submit(as_user(factories.user()), title=title, **fields)

	assert_html(r, 400)
	assert_in_payload(r, title)


def test_a_title_just_short_enough_once_rendered_is_accepted():
	assert_html(_submit(as_user(factories.user()), title='"' * 250, body="x"), 200)


def test_a_title_too_long_once_rendered_is_refused():
	client = as_user(factories.user())

	with db_diff() as d:
		r = _submit(client, headers=XHR, title='"' * 251, body="x")

	assert_status(r, 400)
	d.assert_exactly()


def test_banned_users_cannot_submit():
	u = factories.user(is_banned=seed.AUTOJANNY_ID, unban_utc=0)

	with db_diff() as d:
		r = _submit(as_user(u), **_text_post())

	assert_html(r, 400)
	d.assert_exactly()


def test_users_whose_ban_has_expired_can_submit():
	u = factories.user(is_banned=seed.AUTOJANNY_ID, unban_utc=1000)

	assert_html(_submit(as_user(u), **_text_post()), 200)


def test_mentioning_more_than_100_users_is_refused():
	body = " ".join(f"@{factories.user()['username']}" for _ in range(101))

	client = as_user(factories.user())

	with db_diff() as d:
		r = _submit(client, headers=XHR, title="t", body=body)

	assert_status(r, 400)
	d.assert_exactly()


# Moderation of new posts

def test_new_posts_can_be_held_for_review():
	site_settings_set("FilterNewPosts", True)
	author = factories.user()

	with db_diff() as d:
		_submit(as_user(author), **_text_post())

	d.assert_exactly(inserted={"submissions": [{"state_mod": "FILTERED"}], "votes": [{"user_id": author["id"]}]})


def test_api_clients_get_their_held_post_in_full():
	site_settings_set("FilterNewPosts", True)
	author = factories.user()
	body = factories.unique("body")

	r = _submit(as_api(factories.api_token(author)), title="t", body=body)

	assert_status(r, 200)
	assert r.json["body"] == body


def test_admins_posts_are_never_held_for_review():
	site_settings_set("FilterNewPosts", True)
	author = factories.admin(1)

	assert_html(_submit(as_user(author), **_text_post()), 200)

	assert db.rows("submissions")[-1]["state_mod"] == "VISIBLE"


# Banned domains

@pytest.mark.parametrize("banned, url", [
	("example.com", "https://example.com/page"),
	("example.com", "https://deep.sub.example.com/page"),
	("sub.example.com", "https://sub.example.com/"),
	("example.com/bad", "https://example.com/bad"),
], ids=["host", "subdomain", "exact subdomain", "host and path"])
def test_links_to_banned_domains_are_refused(banned, url):
	db.insert("banneddomains", domain=banned, reason=factories.unique("reason"))

	client = as_user(factories.user())

	with db_diff() as d:
		r = _submit(client, headers=XHR, title="t", url=url)

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("banned, url", [
	("sub.example.com", "https://example.com/"),
	("example.com/bad", "https://example.com/badder"),
	("example.com", "https://notexample.com/"),
], ids=["parent of banned subdomain", "path extending the banned one", "similar host"])
def test_links_merely_near_banned_domains_are_accepted(banned, url):
	db.insert("banneddomains", domain=banned, reason="r")

	assert_html(_submit(as_user(factories.user()), title="t", url=url), 200)


@pytest.mark.parametrize("banned, url", [
	("example.com", "https://EXAMPLE.com/page"),
	("Example.COM", "https://example.com/page"),
	("example.com", "https://example.com:8443/page"),
	("example.com", "https://someone@example.com/page"),
	("example.com", "https://example.com./page"),
	("example.com/bad", "https://example.com/bad/"),
	("example.com/bad", "https://example.com/bad/deeper"),
], ids=["host case", "stored case", "port", "userinfo", "trailing dot", "banned path with a slash", "below a banned path"])
def test_banned_domains_match_however_the_link_is_written(banned, url):
	db.insert("banneddomains", domain=banned, reason="r")
	client = as_user(factories.user())

	with db_diff() as d:
		r = _submit(client, headers=XHR, title="t", url=url)

	assert_status(r, 403)
	d.assert_exactly()


def test_banned_domains_in_the_body_are_refused():
	db.insert("banneddomains", domain="example.com", reason="r")

	client = as_user(factories.user())

	with db_diff() as d:
		r = _submit(client, headers=XHR, title="t", body="see https://example.com/page")

	assert_status(r, 403)
	d.assert_exactly()


# Duplicates

def test_a_link_already_posted_redirects_to_the_earlier_post():
	earlier = factories.post(factories.user(), url="https://example.com/page")

	client = as_user(factories.user())

	with db_diff() as d:
		r = _submit(client, title="t", url="https://example.com/page")

	assert_redirect(r, f"/post/{earlier['id']}/{earlier['title']}")
	d.assert_exactly()


@pytest.mark.parametrize("state", [{"state_mod": "REMOVED"}, {"state_user_deleted_utc": "2020-01-01T00:00:00Z"}], ids=["removed", "deleted"])
def test_links_of_removed_or_deleted_posts_can_be_posted_again(state):
	factories.post(factories.user(), url="https://example.com/page", **state)

	assert_html(_submit(as_user(factories.user()), title="t", url="https://example.com/page"), 200)


def test_a_link_posted_earlier_in_another_form_redirects_too():
	earlier = factories.post(factories.user(), url="http://example.com/page/")

	assert_redirect(_submit(as_user(factories.user()), title="t", url="https://example.com/page?utm_source=x"), f"/post/{earlier['id']}/{earlier['title']}")


@pytest.mark.parametrize("hidden", ["draft", "shadowbanned author"])
def test_links_only_others_cannot_see_can_be_posted_again(hidden):
	author = factories.user(shadowbanned="somemod" if hidden == "shadowbanned author" else None)
	factories.post(author, url="https://example.com/page", private=hidden == "draft")

	assert_html(_submit(as_user(factories.user()), title="t", url="https://example.com/page"), 200)


def test_resubmitting_an_identical_post_redirects_to_it():
	author = factories.user()
	fields = _text_post()
	assert_html(_submit(as_user(author), **fields), 200)
	earlier = db.rows("submissions")[-1]

	with db_diff() as d:
		r = _submit(as_user(author), **fields)

	assert_redirect(r, f"/post/{earlier['id']}/{fields['title']}")
	d.assert_exactly()


def test_resubmitting_a_post_already_duplicated_redirects_to_the_earliest():
	author = factories.user()
	earliest = factories.post(author, title="same", body="same")
	factories.post(author, title="same", body="same")

	assert_redirect(_submit(as_user(author), title="same", body="same"), f"/post/{earliest['id']}/same")


def test_resubmitting_an_identical_draft_makes_a_new_post():
	author = factories.user()
	factories.post(author, title="same", body="same", private=True)

	assert_html(_submit(as_user(author), title="same", body="same"), 200)


def test_identical_posts_by_different_authors_are_both_accepted():
	fields = _text_post()
	assert_html(_submit(as_user(factories.user()), **fields), 200)

	assert_html(_submit(as_user(factories.user()), **fields), 200)


# Spam

def _similar_posts(author, count, **fields):
	for _ in range(count):
		factories.post(author, title="buy cheap watches here", body=factories.unique("body"), **fields)


@pytest.mark.parametrize("age_days, allowed", [(0, 9), (1, 19), (7, 29)])
def test_similar_posts_up_to_the_spam_threshold_are_accepted(age_days, allowed):
	'''New accounts may make 9 similar posts a day before the next is spam; day-old accounts 19, week-old ones 29.'''
	author = factories.user()
	db.update("users", {"id": author["id"]}, created_utc=author["created_utc"] - age_days * 86400 - 60)
	_similar_posts(author, allowed)

	assert_html(_submit(as_user(author), title="buy cheap watches here", body=factories.unique("body")), 200)


@pytest.mark.parametrize("age_days, threshold", [(0, 10), (1, 20), (7, 30)])
def test_spam_bans_the_author_for_a_day_and_removes_their_similar_posts(age_days, threshold):
	author = factories.user()
	db.update("users", {"id": author["id"]}, created_utc=author["created_utc"] - age_days * 86400 - 60)
	_similar_posts(author, threshold)
	similar = [p["id"] for p in db.rows("submissions", author_id=author["id"])]

	with db_diff() as d:
		r = _submit(as_user(author), headers=XHR, title="buy cheap watches here", body=factories.unique("body"))

	assert_status(r, 403)
	d.assert_exactly(
		updated={
			"users": {author["id"]: {"is_banned": seed.AUTOJANNY_ID, "unban_utc": ANY, "ban_reason": "Spamming.", "post_count": 0}},
			"submissions": {pid: {"state_mod": "REMOVED", "state_mod_set_by": "AutoJanny"} for pid in similar},
		},
		inserted={
			"modactions": [{"kind": "remove_post", "user_id": seed.AUTOJANNY_ID, "target_submission_id": pid, "_note": "spam"} for pid in similar],
			"comments": [{"author_id": seed.SYSTEM_ID, "parent_submission": None}],
			"notifications": [{"user_id": author["id"]}],
		},
	)


def test_similar_links_count_as_spam_too():
	author = factories.user()
	for i in range(10):
		factories.post(author, title=factories.unique("title"), url="https://example.com/watches-for-sale")

	assert_status(_submit(as_user(author), headers=XHR, title=factories.unique("title"), url="https://example.com/watches-for-sale-2"), 403)


def test_posts_similar_in_both_title_and_link_are_removed_once():
	author = factories.user()
	_similar_posts(author, 10, url="https://example.com/watches-for-sale")
	similar = [p["id"] for p in db.rows("submissions", author_id=author["id"])]

	_submit(as_user(author), headers=XHR, title="buy cheap watches here", url="https://example.com/watches-for-sale-2")

	assert sorted(m["target_submission_id"] for m in db.rows("modactions", kind="remove_post")) == similar


def test_similar_posts_older_than_a_day_do_not_count():
	author = factories.user()
	_similar_posts(author, 10, created_utc=1000)

	assert_html(_submit(as_user(author), title="buy cheap watches here", body=factories.unique("body")), 200)


# Notifications

def test_publishing_notifies_mentioned_users_and_followers():
	mentioned, follower = factories.user(), factories.user()
	author = factories.user()
	db.insert("follows", user_id=follower["id"], target_id=author["id"])

	with db_diff() as d:
		_submit(as_user(author), title=factories.unique("title"), body=f"hi @{mentioned['username']}")

	d.assert_exactly(
		inserted={
			"submissions": [{"author_id": author["id"]}],
			"votes": [{"user_id": author["id"]}],
			"comments": [{"author_id": seed.SYSTEM_ID, "parent_submission": None}, {"author_id": seed.AUTOJANNY_ID, "parent_submission": None}],
			"notifications": [{"user_id": mentioned["id"], "read": False}, {"user_id": follower["id"], "read": False}],
		},
		updated={"users": {author["id"]: {"post_count": 1}}},
	)


def test_mentions_in_the_title_notify_too():
	mentioned = factories.user()

	assert_html(_submit(as_user(factories.user()), title=f"hi @{mentioned['username']}", body="x"), 200)

	assert len(db.rows("notifications", user_id=mentioned["id"])) == 1


@pytest.mark.parametrize("blocker", ["mentioned", "author"])
def test_mentions_across_a_block_do_not_notify(blocker):
	mentioned = factories.user()
	author = factories.user()
	a, b = (mentioned, author) if blocker == "mentioned" else (author, mentioned)
	db.insert("userblocks", user_id=a["id"], target_id=b["id"])

	assert_html(_submit(as_user(author), title="t", body=f"hi @{mentioned['username']}"), 200)

	assert db.rows("notifications", user_id=mentioned["id"]) == []


def test_mentioning_yourself_does_not_notify():
	author = factories.user()

	assert_html(_submit(as_user(author), title="t", body=f"me @{author['username']}"), 200)

	assert db.rows("notifications", user_id=author["id"]) == []


def test_drafts_notify_nobody():
	mentioned, follower = factories.user(), factories.user()
	author = factories.user()
	db.insert("follows", user_id=follower["id"], target_id=author["id"])

	assert_html(_submit(as_user(author), title="t", body=f"hi @{mentioned['username']}", private="1"), 200)

	assert db.rows("notifications") == []


def _audience(author):
	mentioned, follower = factories.user(), factories.user()
	db.insert("follows", user_id=follower["id"], target_id=author["id"])
	return mentioned


def test_posts_held_for_review_notify_nobody_yet():
	site_settings_set("FilterNewPosts", True)
	author = factories.user()
	mentioned = _audience(author)

	assert_html(_submit(as_user(author), title="t", body=f"hi @{mentioned['username']}"), 200)

	assert db.rows("notifications") == []


def test_posts_by_shadowbanned_users_notify_nobody():
	author = factories.user(shadowbanned="somemod")
	mentioned = _audience(author)

	assert_html(_submit(as_user(author), title="t", body=f"hi @{mentioned['username']}"), 200)

	assert db.rows("notifications") == []


def _approve(post):
	return as_user(factories.admin(2)).post_json("/admin/update_filter_status", {"post_id": post["id"], "new_status": "normal"})


def test_approving_a_held_post_notifies():
	site_settings_set("FilterNewPosts", True)
	author = factories.user()
	mentioned = _audience(author)
	assert_html(_submit(as_user(author), title="t", body=f"hi @{mentioned['username']}"), 200)
	post = db.rows("submissions")[-1]

	assert_status(_approve(post), 200)

	assert {n["user_id"] for n in db.rows("notifications")} == {mentioned["id"], db.row("follows", target_id=author["id"])["user_id"]}


def test_approving_a_held_post_counts_it():
	site_settings_set("FilterNewPosts", True)
	author = factories.user()
	assert_html(_submit(as_user(author), title="t", body="text"), 200)
	post = db.rows("submissions")[-1]

	assert_status(_approve(post), 200)

	assert db.row("users", id=author["id"])["post_count"] == 1


def test_removing_a_post_from_the_review_queue_uncounts_it():
	author = factories.user()
	post = factories.post(author)

	as_user(factories.admin(2)).post_json("/admin/update_filter_status", {"post_id": post["id"], "new_status": "removed"})

	assert db.row("users", id=author["id"])["post_count"] == 0


def test_approving_a_post_twice_does_not_notify_twice():
	author = factories.user()
	mentioned = _audience(author)
	assert_html(_submit(as_user(author), title="t", body=f"hi @{mentioned['username']}"), 200)
	post = db.rows("submissions")[-1]
	moderator = as_user(factories.admin(2))
	moderator.post_json("/admin/update_filter_status", {"post_id": post["id"], "new_status": "removed"})

	moderator.post_json("/admin/update_filter_status", {"post_id": post["id"], "new_status": "normal"})

	assert len(db.rows("notifications")) == 2


def test_later_mentions_of_the_same_post_share_one_notification():
	first, second = factories.user(), factories.user()
	author = factories.user()
	assert_html(_submit(as_user(author), title="t", body=f"hi @{first['username']} @{second['username']}"), 200)

	notified = db.rows("notifications")
	assert {n["user_id"] for n in notified} == {first["id"], second["id"]}
	assert len({n["comment_id"] for n in notified}) == 1


# Images

def _image_paths(text):
	return sorted(set(re.findall(r"/images/[^\s\"<>)]+", text)))


def test_image_post():
	author = factories.user()

	with db_diff() as d:
		r = _submit(as_user(author), title=factories.unique("title"), files={"file": uploads.png(64, 64)})

	assert_html(r, 200)
	d.assert_exactly(
		inserted={"submissions": [{"url": ANY, "thumburl": ANY, "body": ""}], "votes": [{"user_id": author["id"]}]},
		updated={"users": {author["id"]: {"post_count": 1}}},
	)
	post = db.rows("submissions")[-1]
	assert post["url"].startswith("/images/") and post["thumburl"].startswith("/images/") and post["url"] != post["thumburl"]
	assert_serves_image(post["url"])
	assert_serves_image(post["thumburl"])


def test_an_image_alongside_a_link_is_ignored():
	assert_html(_submit(as_user(factories.user()), title="t", url="https://example.com/page", files={"file": uploads.png(64, 64)}), 200)

	post = db.rows("submissions")[-1]
	assert (post["url"], post["thumburl"]) == ("https://example.com/page", None)


def test_image_posts_must_be_images():
	client = as_user(factories.user())

	with db_diff() as d:
		r = _submit(client, headers=XHR, title="t", files={"file": uploads.text_file()})

	assert_status(r, 415)
	d.assert_exactly()


def test_images_from_tor_are_dropped():
	client = as_user(factories.user())

	with db_diff() as d:
		r = _submit(client, headers={**XHR, **TOR}, title="t", files={"file": uploads.png(64, 64)})

	assert_status(r, 400)
	d.assert_exactly()


def test_body_images_are_linked_at_the_end_of_the_body():
	assert_html(_submit(as_user(factories.user()), title="t", body="text", files={"file2": [uploads.png(20, 20), uploads.png(30, 30)]}), 200)

	body = db.rows("submissions")[-1]["body"]
	images = _image_paths(body)
	assert body.startswith("text") and len(images) == 2
	for image in images:
		assert_serves_image(image)


def test_body_images_alone_make_a_post():
	assert_html(_submit(as_user(factories.user()), title="t", files={"file2": [uploads.png(20, 20)]}), 200)

	assert len(_image_paths(db.rows("submissions")[-1]["body"])) == 1


def test_body_images_may_not_push_the_body_past_its_limit():
	client = as_user(factories.user())

	with db_diff() as d:
		r = _submit(client, headers=XHR, title="t", body="b" * 499990, files={"file2": [uploads.png(20, 20)]})

	assert_status(r, 400)
	d.assert_exactly()


def test_at_most_four_body_images_are_kept():
	assert_html(_submit(as_user(factories.user()), title="t", body="text", files={"file2": [uploads.png(20, 20)] * 5}), 200)

	assert len(_image_paths(db.rows("submissions")[-1]["body"])) == 4


def test_body_images_must_be_images():
	client = as_user(factories.user())

	with db_diff() as d:
		r = _submit(client, headers=XHR, title="t", body="text", files={"file2": [uploads.png(20, 20), uploads.text_file()]})

	assert_status(r, 415)
	d.assert_exactly()


def test_an_empty_body_image_slot_is_ignored():
	assert_html(_submit(as_user(factories.user()), title="t", body="text", files={"file2": [("", b"", "application/octet-stream")]}), 200)

	assert db.rows("submissions")[-1]["body"] == "text"


def test_body_images_from_tor_are_dropped():
	_submit(as_user(factories.user()), headers=TOR, title="t", body="text", files={"file2": [uploads.png(20, 20)]})

	assert db.rows("submissions")[-1]["body"] == "text"


# Embeds

TWEET = f"https://twitter.com/someone/status/{123}"


def test_tweets_are_embedded():
	embed = f"<blockquote>{factories.unique('tweet')}</blockquote>"
	external_web.serve("https://publish.twitter.com/oembed", headers={"Content-Type": "application/json"}, body=json.dumps({"html": embed}))
	assert_html(_submit(as_user(factories.user()), title="t", url=TWEET), 200)

	assert db.rows("submissions")[-1]["embed_url"] == embed
	[(method, requested)] = external_web.requests()
	assert parse_qs(urlsplit(requested).query)["url"] == [TWEET]


def test_tweets_that_cannot_be_fetched_are_not_embedded():
	external_web.unreachable("https://publish.twitter.com/oembed")

	assert_html(_submit(as_user(factories.user()), title="t", url=TWEET), 200)

	assert db.rows("submissions")[-1]["embed_url"] is None


def test_oversized_embeds_are_dropped():
	external_web.serve("https://publish.twitter.com/oembed", body=json.dumps({"html": "x" * 1501}))

	assert_html(_submit(as_user(factories.user()), title="t", url=TWEET), 200)

	assert db.rows("submissions")[-1]["embed_url"] is None


def test_youtube_videos_are_embedded_from_their_start_time():
	external_web.serve("https://www.googleapis.com/youtube/v3/videos", body=json.dumps({"items": [{}]}))

	assert_html(_submit(as_user(factories.user()), title="t", url="https://youtube.com/watch?v=dQw4w9WgXcQ&t=42s"), 200)

	embed = db.rows("submissions")[-1]["embed_url"]
	assert "dQw4w9WgXcQ" in embed and "start=42" in embed
	[(method, requested)] = external_web.requests()
	assert parse_qs(urlsplit(requested).query)["id"] == ["dQw4w9WgXcQ"]


def test_youtube_videos_that_do_not_exist_are_not_embedded():
	external_web.serve("https://www.googleapis.com/youtube/v3/videos", body=json.dumps({"items": []}))

	assert_html(_submit(as_user(factories.user()), title="t", url="https://youtube.com/watch?v=dQw4w9WgXcQ"), 200)

	assert db.rows("submissions")[-1]["embed_url"] is None


def test_youtube_videos_that_cannot_be_looked_up_are_not_embedded():
	external_web.unreachable("https://www.googleapis.com/youtube/v3/videos")

	assert_html(_submit(as_user(factories.user()), title="t", url="https://youtube.com/watch?v=dQw4w9WgXcQ"), 200)

	assert db.rows("submissions")[-1]["embed_url"] is None


def test_youtube_start_times_that_are_not_numbers_are_ignored():
	external_web.serve("https://www.googleapis.com/youtube/v3/videos", body=json.dumps({"items": [{}]}))

	assert_html(_submit(as_user(factories.user()), title="t", url="https://youtube.com/watch?v=dQw4w9WgXcQ&t=soon"), 200)

	embed = db.rows("submissions")[-1]["embed_url"]
	assert "dQw4w9WgXcQ" in embed and "start=" not in embed


def test_youtube_links_with_malformed_ids_are_not_looked_up():
	assert_html(_submit(as_user(factories.user()), title="t", url="https://youtube.com/watch?v=no!"), 200)

	assert db.rows("submissions")[-1]["embed_url"] is None
