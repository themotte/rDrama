'''
A comment's own page: GET /comment/<comment id> and GET /post/<post id>/<anything>/<comment id> (the middle segment is a cosmetic slug and is ignored). It shows the comment's post with the comment and its replies in place of the post's comments. An unknown comment, a comment id or post id that isn't one (spec/harness/routes.py), or a comment on another post than the one named is 404 (the last is pinned with the post page).

- "context" (a whole number; values above 8 mean 8, values below 0 and anything not a number mean 0) shows that many of the comment's ancestors above it, each with only the next comment of the chain under it (their other replies are left out). Without it, the comment is shown alone, without its parent.
- The comment's replies are shown under it, nested to a depth of nine levels counted from the topmost comment shown (so each ancestor brought in by "context" leaves one level fewer for the replies).
- "sort" orders the replies as on the post page; an unknown value means the viewer's default.
- "read" (any non-empty value) marks the viewer's unread notification about this comment as read, when the page is shown to them. Anonymous viewers, viewers without such a notification and refused requests change nothing.
- A private message (a comment with no post, sent to a user) is refused with 403 to anyone who isn't its sender or recipient or taking part in its conversation (admins from level 2 may open any), visitors included. Its page shows its conversation instead of a post (notifications/test_message_page). "context" never brings in a private message the viewer couldn't open itself: the chain stops below it.
- On an 18+ post, browsers of visitors and of users who are not 18+ get the age confirmation page instead of the comment until they confirm (POST /allow_nsfw); scripts (xhr) and API clients of users who are not 18+ are refused with 403; users who are 18+ see the comment.
- The page describes the comment (its text and author, for link previews) only to viewers who may see it.
- API clients get the JSON object of the topmost comment shown (see test_json.py for its shape), with the chain down to the comment as its replies.
'''
import pytest

from files.tests.spec.harness import *

FORMS = {
	"comment": lambda post, comment: f"/comment/{comment['id']}",
	"post": lambda post, comment: f"/post/{post['id']}/anything/{comment['id']}",
}


@pytest.mark.parametrize("form", FORMS)
def test_permalink_shows_the_comment_and_its_replies(form):
	post = factories.post(factories.user())
	comment = factories.comment(factories.user(), post)
	reply = factories.comment(factories.user(), post, parent=comment)

	r = anon().get(FORMS[form](post, comment))

	assert_html(r, 200)
	assert_in_payload(r, post["title"])
	assert_in_payload(r, comment["body"])
	assert_in_payload(r, reply["body"])


@pytest.mark.parametrize("form", FORMS)
def test_permalink_leaves_out_the_rest_of_the_post(form):
	post = factories.post(factories.user())
	comment = factories.comment(factories.user(), post)
	other = factories.comment(factories.user(), post)

	r = anon().get(FORMS[form](post, comment))

	assert_html(r, 200)
	assert_not_in_payload(r, other["body"])


def _gone_comment():
	comment = factories.comment(factories.user(), factories.post(factories.user()))
	db.delete("commentvotes", comment_id=comment["id"])
	db.delete("comments", id=comment["id"])
	return comment


@pytest.mark.parametrize("form", FORMS)
def test_unknown_comments_are_not_found(form):
	post = factories.post(factories.user())

	assert_status(anon().get(FORMS[form](post, _gone_comment())), 404)


@pytest.mark.parametrize("form", FORMS)
def test_comment_ids_that_are_not_numbers_are_not_found(form):
	post = factories.post(factories.user())

	assert_status(anon().get(FORMS[form](post, {"id": "abc"})), 404)


def test_post_ids_that_are_not_numbers_are_not_found():
	comment = factories.comment(factories.user(), factories.post(factories.user()))

	assert_status(anon().get(f"/post/abc/anything/{comment['id']}"), 404)


# Context

def _chain(post, length):
	'''A thread `length` comments deep, each replying to the one before.'''
	chain = [factories.comment(factories.user(), post)]
	for _ in range(length - 1):
		chain.append(factories.comment(factories.user(), post, parent=chain[-1]))
	return chain


@pytest.mark.parametrize("context, shown", [("0", 0), ("1", 1), ("3", 3), ("8", 8), ("9", 8), ("100", 8), ("-1", 0), ("-5", 0), ("abc", 0), ("", 0)])
def test_context_shows_that_many_ancestors(context, shown):
	post = factories.post(factories.user())
	chain = _chain(post, 10)
	focus = chain[-1]

	r = anon().get(f"/comment/{focus['id']}", params={"context": context})

	assert_html(r, 200)
	assert_in_payload(r, focus["body"])
	ancestors = list(reversed(chain[:-1]))
	for ancestor in ancestors[:shown]:
		assert_in_payload(r, ancestor["body"])
	for ancestor in ancestors[shown:]:
		assert_not_in_payload(r, ancestor["body"])


def test_context_stops_at_the_top_level_comment():
	post = factories.post(factories.user())
	top, focus = _chain(post, 2)

	r = anon().get(f"/comment/{focus['id']}", params={"context": "8"})

	assert_html(r, 200)
	assert_in_payload(r, top["body"])
	assert_in_payload(r, focus["body"])


def test_context_leaves_out_the_ancestors_other_replies():
	post = factories.post(factories.user())
	top, middle, focus = _chain(post, 3)
	uncle = factories.comment(factories.user(), post, parent=top)
	sibling = factories.comment(factories.user(), post, parent=middle)

	r = anon().get(f"/comment/{focus['id']}", params={"context": "2"})

	assert_html(r, 200)
	assert_in_payload(r, top["body"])
	assert_in_payload(r, middle["body"])
	assert_not_in_payload(r, uncle["body"])
	assert_not_in_payload(r, sibling["body"])


@pytest.mark.parametrize("context", [0, 3])
def test_replies_are_shown_nine_levels_deep_counting_from_the_topmost_comment_shown(context):
	post = factories.post(factories.user())
	chain = _chain(post, context + 1 + 9)
	focus = chain[context]
	deepest_shown = chain[8]

	r = anon().get(f"/comment/{focus['id']}", params={"context": str(context)})

	assert_html(r, 200)
	assert_in_payload(r, chain[0]["body"])
	assert_in_payload(r, deepest_shown["body"])
	assert_not_in_payload(r, chain[9]["body"])


# Marking notifications read

def _notified(viewer, comment, read=False):
	db.insert("notifications", user_id=viewer["id"], comment_id=comment["id"], read=read)


def test_read_marks_the_viewers_notification_about_the_comment_read():
	viewer = factories.user()
	comment = factories.comment(factories.user(), factories.post(factories.user()))
	_notified(viewer, comment)
	client = as_user(viewer)

	with db_diff() as d:
		r = client.get(f"/comment/{comment['id']}", params={"read": "1"})

	assert_html(r, 200)
	d.assert_exactly(updated={"notifications": {(viewer["id"], comment["id"]): {"read": True}}})


@pytest.mark.parametrize("what", ["someone else's message", "comment on someone else's draft"])
def test_read_changes_nothing_when_the_comment_is_refused(what):
	viewer = factories.user()
	if what == "someone else's message":
		comment, status = _message(factories.user(), factories.user()), 403
	else:
		comment, status = factories.comment(factories.user(), factories.post(factories.user(), private=True)), 404
	_notified(viewer, comment)
	client = as_user(viewer)

	with db_diff() as d:
		r = client.get(f"/comment/{comment['id']}", params={"read": "1"})

	assert_status(r, status)
	d.assert_exactly()


def test_without_read_notifications_stay_unread():
	viewer = factories.user()
	comment = factories.comment(factories.user(), factories.post(factories.user()))
	_notified(viewer, comment)
	client = as_user(viewer)

	with db_diff() as d:
		r = client.get(f"/comment/{comment['id']}")

	assert_html(r, 200)
	d.assert_exactly()


def test_read_leaves_other_users_notifications_alone():
	viewer = factories.user()
	comment = factories.comment(factories.user(), factories.post(factories.user()))
	_notified(factories.user(), comment)
	client = as_user(viewer)

	with db_diff() as d:
		r = client.get(f"/comment/{comment['id']}", params={"read": "1"})

	assert_html(r, 200)
	d.assert_exactly()


def test_read_by_visitors_changes_nothing():
	comment = factories.comment(factories.user(), factories.post(factories.user()))
	_notified(factories.user(), comment)

	with db_diff() as d:
		r = anon().get(f"/comment/{comment['id']}", params={"read": "1"})

	assert_html(r, 200)
	d.assert_exactly()


def test_read_leaves_notifications_about_other_comments_alone():
	viewer = factories.user()
	post = factories.post(factories.user())
	comment = factories.comment(factories.user(), post)
	_notified(viewer, factories.comment(factories.user(), post))
	client = as_user(viewer)

	with db_diff() as d:
		r = client.get(f"/comment/{comment['id']}", params={"read": "1"})

	assert_html(r, 200)
	d.assert_exactly()


# Private messages

def _message(author, recipient):
	return factories.message(author, recipient, created_utc=1000)


@pytest.mark.parametrize("viewer", ["visitor", "user", "helper"])
def test_private_messages_are_refused_to_non_participants(viewer):
	message = _message(factories.user(), factories.user())
	client = {"visitor": anon, "user": lambda: as_user(factories.user()), "helper": lambda: as_user(factories.admin(1))}[viewer]()

	r = client.get(f"/comment/{message['id']}")

	assert_status(r, 403)
	assert_not_in_payload(r, message["text"])



def test_context_stops_below_messages_the_viewer_cant_open():
	sender, recipient, outsider = factories.user(), factories.user(), factories.user()
	message = _message(sender, recipient)
	client = as_user(outsider)
	# Older versions let anyone answer any message
	reply = factories.message(outsider, sender, message)

	r = client.get(f"/comment/{reply['id']}", params={"context": 8})

	assert_html(r, 200)
	assert_in_payload(r, reply["body_html"])
	assert_not_in_payload(r, message["text"])


@pytest.mark.parametrize("why", ["blocked", "shadowbanned", "removed"])
def test_the_page_doesnt_describe_comments_hidden_from_the_viewer(why):
	viewer = factories.user()
	author = factories.user(shadowbanned="somemod") if why == "shadowbanned" else factories.user()
	if why == "blocked":
		db.insert("userblocks", user_id=viewer["id"], target_id=author["id"])
	comment = factories.comment(author, factories.post(factories.user()), body=factories.unique(), **({"state_mod": "REMOVED", "state_mod_set_by": "somemod"} if why == "removed" else {}))

	r = as_user(viewer).get(f"/comment/{comment['id']}")

	assert_html(r, 200)
	assert_not_in_payload(r, comment["body"])


def test_an_unknown_sort_uses_the_viewers_default_and_isnt_echoed():
	marker = factories.unique("injected")
	post = factories.post(factories.user())
	focus = factories.comment(factories.user(), post)
	newer = factories.comment(factories.user(), post, parent=focus, created_utc=2000)
	older = factories.comment(factories.user(), post, parent=focus, created_utc=1000)

	r = as_user(factories.user(defaultsortingcomments="old")).get(f"/comment/{focus['id']}", params={"sort": f"');{marker}//"})

	assert_html(r, 200)
	assert_not_in_payload(r, marker)
	assert r.text.index(older["body"]) < r.text.index(newer["body"])

# 18+ posts

def _comment_on_18_plus_post():
	post = factories.post(factories.user(), over_18=True)
	return factories.comment(factories.user(), post)


def test_visitors_must_confirm_their_age_before_seeing_a_comment_on_an_18_plus_post():
	comment = _comment_on_18_plus_post()

	r = anon().get(f"/comment/{comment['id']}")

	assert_html(r, 200)
	assert_not_in_payload(r, comment["body"])


@pytest.mark.parametrize("client", ["api", "xhr"])
def test_scripts_are_refused_comments_on_18_plus_posts_without_confirmation(client):
	comment = _comment_on_18_plus_post()
	user = factories.user()

	if client == "api":
		r = as_api(factories.api_token(user)).get(f"/comment/{comment['id']}")
	else:
		r = as_user(user).get(f"/comment/{comment['id']}", headers=XHR)

	assert_status(r, 403)
	assert_not_in_payload(r, comment["body"])


def test_users_who_are_not_18_plus_must_confirm_too():
	comment = _comment_on_18_plus_post()

	r = as_user(factories.user()).get(f"/comment/{comment['id']}")

	assert_html(r, 200)
	assert_not_in_payload(r, comment["body"])


def test_confirming_age_shows_comments_on_18_plus_posts_to_visitors():
	comment = _comment_on_18_plus_post()
	visitor = anon()
	path = f"/comment/{comment['id']}"

	assert_redirect(visitor.post("/allow_nsfw", {"redir": path}), path)
	r = visitor.get(path)

	assert_html(r, 200)
	assert_in_payload(r, comment["body"])


def test_users_who_are_18_plus_see_comments_on_18_plus_posts():
	comment = _comment_on_18_plus_post()

	r = as_user(factories.user(over_18=True)).get(f"/comment/{comment['id']}")

	assert_html(r, 200)
	assert_in_payload(r, comment["body"])


# API

def test_api_clients_get_the_topmost_comment_shown_with_the_chain_below_it():
	post = factories.post(factories.user())
	top, focus = _chain(post, 2)
	factories.comment(factories.user(), post, parent=top)
	focus_reply = factories.comment(factories.user(), post, parent=focus)

	r = as_api(factories.api_token(factories.user())).get(f"/comment/{focus['id']}", params={"context": "1"})

	assert_status(r, 200)
	assert r.json["id"] == top["id"]
	assert [c["id"] for c in r.json["replies"]] == [focus["id"]]
	assert [c["id"] for c in r.json["replies"][0]["replies"]] == [focus_reply["id"]]


def test_api_clients_without_context_get_the_comment_itself():
	post = factories.post(factories.user())
	top, focus = _chain(post, 2)

	r = as_api(factories.api_token(factories.user())).get(f"/comment/{focus['id']}")

	assert_status(r, 200)
	assert r.json["id"] == focus["id"]
