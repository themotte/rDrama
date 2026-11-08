'''
GET /stats shows admins (level 2+) figures about the whole site, as of the request. Each is the text of the element with id "stat-<name>":
- users: accounts; private_users: those with a private profile; banned_users: those under a suspension, temporary or permanent; verified_email_users: those who verified an email address; signups_24h: accounts made in the last 24 hours.
- posts: all posts, drafts, removed and deleted ones included; posting_users: accounts that made any post; listed_posts: posts neither removed (or filtered) by moderators nor deleted by their authors; removed_posts: posts moderators removed or filtered; deleted_posts: posts their authors deleted; posts_24h: posts made in the last 24 hours.
- comments: comments (private messages included) not by the system accounts; commenting_users: accounts that made any comment, the system accounts included; removed_comments and deleted_comments: as for posts; comments_24h: comments not by the system accounts made in the last 24 hours.
- post_votes and comment_votes: votes cast; post_voting_users and comment_voting_users: accounts that cast any; upvotes and downvotes: votes of each kind on posts and comments together. Posting and commenting count as the author's own upvote.
- active_users_7d: accounts that posted, commented or voted in the last 7 days.

GET /weekly_chart and /daily_chart (and /chart, which redirects to the weekly one) are PNG images, for admins too, charting the 46 whole UTC weeks or days before today's UTC midnight, oldest first, each labelled with its first day as "dd/mm": in each, how many accounts signed up, and how many posts and how many comments not by the system accounts were made in it and are visible (neither removed nor filtered). A row counts in the span from whose first second it was made up to the next span's; today so far isn't shown. Their content is an image, so only that they're served is checked here.
'''
import time

import pytest

from files.tests.spec.harness import *


def test_the_page_is_current_for_its_viewer():
	admin = factories.admin(2)
	client = as_user(admin)
	before = notification_counts(client.get("/stats"))["bell"]
	factories.notification(admin, factories.comment(factories.user(), factories.post(factories.user())))

	r = client.get("/stats")

	assert_html(r, 200)
	assert notification_counts(r)["bell"] == before + 1


@pytest.mark.parametrize("path", ["/weekly_chart", "/daily_chart"])
def test_the_charts_are_png_images(path):
	r = as_user(factories.admin(2)).get(path)

	assert_status(r, 200)
	assert r.header("Content-Type") == "image/png" and r.body.startswith(b"\x89PNG\r\n\x1a\n")


DAY = 86400
REMOVED = {"state_mod": "REMOVED", "state_mod_set_by": "somemod"}
DELETED = {"state_user_deleted_utc": "2020-01-01T00:00:00Z"}


def _old():
	return int(time.time()) - 2 * DAY


# (figure, what is added, how, by how much the figure moves); `w` holds an author, their post and a comment on it, made before the first look
CELLS = [
	("users", "an account", lambda w: factories.user(created_utc=0), 1),
	("private_users", "a private account", lambda w: factories.user(is_private=True), 1),
	("private_users", "a public account", lambda w: factories.user(), 0),
	("banned_users", "a suspended account", lambda w: factories.user(is_banned=seed.SYSTEM_ID, unban_utc=int(time.time()) + DAY), 1),
	("banned_users", "an unsuspended account", lambda w: factories.user(), 0),
	("verified_email_users", "a verified account", lambda w: factories.user(is_activated=True), 1),
	("verified_email_users", "an unverified account", lambda w: factories.user(is_activated=False), 0),
	("signups_24h", "a new account", lambda w: factories.user(), 1),
	("signups_24h", "an account two days old", lambda w: factories.user(created_utc=_old()), 0),
	("posts", "a post", lambda w: factories.post(w["author"]), 1),
	("posts", "a draft", lambda w: factories.post(w["author"], private=True), 1),
	("posts", "a removed post", lambda w: factories.post(w["author"], **REMOVED), 1),
	("posting_users", "two posts by a new poster", lambda w: [factories.post(u := factories.user()), factories.post(u)], 1),
	("posting_users", "a post by a poster", lambda w: factories.post(w["author"]), 0),
	("listed_posts", "a post", lambda w: factories.post(w["author"]), 1),
	("listed_posts", "a removed post", lambda w: factories.post(w["author"], **REMOVED), 0),
	("listed_posts", "a filtered post", lambda w: factories.post(w["author"], state_mod="FILTERED"), 0),
	("listed_posts", "a deleted post", lambda w: factories.post(w["author"], **DELETED), 0),
	("removed_posts", "a removed post", lambda w: factories.post(w["author"], **REMOVED), 1),
	("removed_posts", "a filtered post", lambda w: factories.post(w["author"], state_mod="FILTERED"), 1),
	("removed_posts", "a post", lambda w: factories.post(w["author"]), 0),
	("deleted_posts", "a deleted post", lambda w: factories.post(w["author"], **DELETED), 1),
	("deleted_posts", "a post", lambda w: factories.post(w["author"]), 0),
	("posts_24h", "a post", lambda w: factories.post(w["author"]), 1),
	("posts_24h", "a post two days old", lambda w: factories.post(w["author"], created_utc=_old()), 0),
	("comments", "a comment", lambda w: factories.comment(w["author"], w["post"]), 1),
	("comments", "a removed comment", lambda w: factories.comment(w["author"], w["post"], **REMOVED), 1),
	("comments", "a private message", lambda w: factories.message(w["author"], factories.user()), 1),
	("comments", "a comment by a system account", lambda w: factories.comment({"id": seed.AUTOJANNY_ID}, w["post"]), 0),
	("commenting_users", "two comments by a new commenter", lambda w: [factories.comment(u := factories.user(), w["post"]), factories.comment(u, w["post"])], 1),
	("commenting_users", "a comment by a system account", lambda w: factories.comment({"id": seed.AUTOJANNY_ID}, w["post"]), 1),
	("removed_comments", "a removed comment", lambda w: factories.comment(w["author"], w["post"], **REMOVED), 1),
	("removed_comments", "a comment", lambda w: factories.comment(w["author"], w["post"]), 0),
	("deleted_comments", "a deleted comment", lambda w: factories.comment(w["author"], w["post"], **DELETED), 1),
	("deleted_comments", "a comment", lambda w: factories.comment(w["author"], w["post"]), 0),
	("comments_24h", "a comment", lambda w: factories.comment(w["author"], w["post"]), 1),
	("comments_24h", "a comment two days old", lambda w: factories.comment(w["author"], w["post"], created_utc=_old()), 0),
	("comments_24h", "a comment by a system account", lambda w: factories.comment({"id": seed.AUTOJANNY_ID}, w["post"]), 0),
	("post_votes", "a downvote on a post", lambda w: factories.vote(factories.user(), w["post"], -1), 1),
	("post_votes", "a post (its author's own upvote)", lambda w: factories.post(w["author"]), 1),
	("post_votes", "a vote on a comment", lambda w: factories.vote(factories.user(), w["comment"], 1), 0),
	("post_voting_users", "two votes by a new voter", lambda w: [factories.vote(u := factories.user(), w["post"], 1), factories.vote(u, factories.post(w["author"]), -1)], 1),
	("comment_votes", "a downvote on a comment", lambda w: factories.vote(factories.user(), w["comment"], -1), 1),
	("comment_votes", "a vote on a post", lambda w: factories.vote(factories.user(), w["post"], 1), 0),
	("comment_voting_users", "a vote by a new voter", lambda w: factories.vote(factories.user(), w["comment"], 1), 1),
	("upvotes", "an upvote on a post and one on a comment", lambda w: [factories.vote(factories.user(), w["post"], 1), factories.vote(factories.user(), w["comment"], 1)], 2),
	("upvotes", "downvotes", lambda w: [factories.vote(factories.user(), w["post"], -1), factories.vote(factories.user(), w["comment"], -1)], 0),
	("downvotes", "a downvote on a post and one on a comment", lambda w: [factories.vote(factories.user(), w["post"], -1), factories.vote(factories.user(), w["comment"], -1)], 2),
	("downvotes", "an upvote", lambda w: factories.vote(factories.user(), w["post"], 1), 0),
	("active_users_7d", "a new commenter", lambda w: factories.comment(factories.user(), w["post"]), 1),
	("active_users_7d", "a new voter", lambda w: factories.vote(factories.user(), w["post"], 1), 1),
	("active_users_7d", "a new account doing nothing", lambda w: factories.user(), 0),
	("active_users_7d", "more from an active account", lambda w: factories.comment(w["author"], w["post"]), 0),
]


@pytest.mark.parametrize("figure, added, arrange, delta", CELLS, ids=[f"{c[0]}: {c[1]}" for c in CELLS])
def test_each_figure_counts_what_it_says(figure, added, arrange, delta):
	author = factories.user()
	post = factories.post(author)
	world = {"author": author, "post": post, "comment": factories.comment(author, post)}
	client = as_user(factories.admin(2))
	before = int(element_text(client.get("/stats"), f"stat-{figure}"))

	arrange(world)

	assert int(element_text(client.get("/stats"), f"stat-{figure}")) == before + delta


def test_chart_redirects_to_the_weekly_chart():
	assert_redirect(as_user(factories.admin(2)).get("/chart"), "/weekly_chart")
