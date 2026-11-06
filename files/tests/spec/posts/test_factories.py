'''
The post, comment and vote factories arrange the same database state as submitting, commenting and voting through the site, so tests that arrange with them describe states real users reach. Notifications aside, which the factories don't send.
'''
import pytest

from files.tests.spec.harness import *

_POST_IDENTITY = {"id", "title", "title_html", "body", "body_html", "created_utc"}
_COMMENT_IDENTITY = {"id", "top_comment_id", "body", "body_html", "created_utc"}


def _without(row, columns):
	return {k: v for k, v in row.items() if k not in columns}


def _vote(table, **where):
	return _without(db.row(table, **where), {"created_datetimez"})


def test_a_factory_post_matches_a_submitted_one():
	submitter, arranger = factories.user(), factories.user()

	as_user(submitter).post("/submit", {"title": factories.unique("title"), "body": factories.unique("body")})
	submitted = db.row("submissions", author_id=submitter["id"])
	arranged = factories.post(arranger, body=factories.unique("body"))

	assert _without(submitted, _POST_IDENTITY | {"author_id"}) == _without(arranged, _POST_IDENTITY | {"author_id"})
	assert _without(_vote("votes", submission_id=submitted["id"]), {"user_id", "submission_id"}) == _without(_vote("votes", submission_id=arranged["id"]), {"user_id", "submission_id"})
	assert db.row("users", id=submitter["id"])["post_count"] == db.row("users", id=arranger["id"])["post_count"] == 1


def _comment_through_the_site(author, parent_fullname):
	r = as_user(author).post("/comment", {"parent_fullname": parent_fullname, "body": factories.unique("comment")})
	assert_status(r, 200)
	return db.rows("comments", author_id=author["id"])[-1]


def _assert_same_comment_state(through_site, arranged, parent_ids):
	ignored = _COMMENT_IDENTITY | {"author_id", "parent_submission", "parent_comment_id"}
	assert _without(through_site, ignored) == _without(arranged, ignored)
	assert _without(_vote("commentvotes", comment_id=through_site["id"]), {"user_id", "comment_id"}) == _without(_vote("commentvotes", comment_id=arranged["id"]), {"user_id", "comment_id"})
	for site_parent, arranged_parent in parent_ids:
		assert db.row("comments", id=site_parent)["descendant_count"] == db.row("comments", id=arranged_parent)["descendant_count"]
	assert db.row("users", id=through_site["author_id"])["comment_count"] == db.row("users", id=arranged["author_id"])["comment_count"]


def test_a_factory_comment_matches_one_made_through_the_site():
	site_post, arranged_post = factories.post(factories.user()), factories.post(factories.user())
	site_author, arranged_author = factories.user(), factories.user()

	through_site = _comment_through_the_site(site_author, f"post_{site_post['id']}")
	arranged = factories.comment(arranged_author, arranged_post)

	_assert_same_comment_state(through_site, arranged, [])
	assert db.row("users", id=site_author["id"])["comment_count"] == 1
	assert through_site["top_comment_id"] == through_site["id"] and arranged["top_comment_id"] == arranged["id"]
	assert db.row("submissions", id=site_post["id"])["comment_count"] == db.row("submissions", id=arranged_post["id"])["comment_count"] == 1


def test_a_factory_reply_matches_one_made_through_the_site():
	site_post, arranged_post = factories.post(factories.user()), factories.post(factories.user())
	site_top = factories.comment(factories.user(), site_post)
	site_middle = factories.comment(factories.user(), site_post, parent=site_top)
	arranged_top = factories.comment(factories.user(), arranged_post)
	arranged_middle = factories.comment(factories.user(), arranged_post, parent=arranged_top)
	site_author, arranged_author = factories.user(), factories.user()

	through_site = _comment_through_the_site(site_author, f"comment_{site_middle['id']}")
	arranged = factories.comment(arranged_author, arranged_post, parent=arranged_middle)

	_assert_same_comment_state(through_site, arranged, [(site_top["id"], arranged_top["id"]), (site_middle["id"], arranged_middle["id"])])
	assert (through_site["top_comment_id"], arranged["top_comment_id"]) == (site_top["id"], arranged_top["id"])
	assert db.row("submissions", id=site_post["id"])["comment_count"] == db.row("submissions", id=arranged_post["id"])["comment_count"] == 3


def test_a_factory_comment_on_an_18_plus_post_matches_one_made_through_the_site():
	site_post, arranged_post = factories.post(factories.user(), over_18=True), factories.post(factories.user(), over_18=True)
	site_author, arranged_author = factories.user(), factories.user()

	through_site = _comment_through_the_site(site_author, f"post_{site_post['id']}")
	arranged = factories.comment(arranged_author, arranged_post)

	_assert_same_comment_state(through_site, arranged, [])


def test_a_factory_comment_by_a_shadowbanned_user_matches_one_made_through_the_site():
	site_top, arranged_top = factories.comment(factories.user(), factories.post(factories.user())), factories.comment(factories.user(), factories.post(factories.user()))
	site_author, arranged_author = factories.user(shadowbanned="somemod"), factories.user(shadowbanned="somemod")

	through_site = _comment_through_the_site(site_author, f"comment_{site_top['id']}")
	arranged = factories.comment(arranged_author, db.row("submissions", id=arranged_top["parent_submission"]), parent=arranged_top)

	_assert_same_comment_state(through_site, arranged, [(site_top["id"], arranged_top["id"])])
	assert db.row("users", id=site_author["id"])["comment_count"] == 1
	assert db.row("submissions", id=site_top["parent_submission"])["comment_count"] == db.row("submissions", id=arranged_top["parent_submission"])["comment_count"] == 1


def test_a_factory_comment_on_a_draft_matches_one_made_through_the_site():
	site_author, arranged_author = factories.user(), factories.user()
	site_post, arranged_post = factories.post(site_author, private=True), factories.post(arranged_author, private=True)

	through_site = _comment_through_the_site(site_author, f"post_{site_post['id']}")
	arranged = factories.comment(arranged_author, arranged_post)

	_assert_same_comment_state(through_site, arranged, [])
	assert db.row("users", id=site_author["id"])["comment_count"] == 0
	assert db.row("submissions", id=site_post["id"])["comment_count"] == db.row("submissions", id=arranged_post["id"])["comment_count"] == 1


@pytest.mark.parametrize("kind", ["post", "comment"])
@pytest.mark.parametrize("votes", [[1], [-1], [1, -1], [1, 0], [-1, 1, 0]])
def test_a_factory_vote_matches_one_cast_through_the_site(kind, votes):
	table, vote_table, key = ("submissions", "votes", "submission_id") if kind == "post" else ("comments", "commentvotes", "comment_id")
	site_author, arranged_author = factories.user(), factories.user()
	site_voter, arranged_voter = factories.user(), factories.user()
	if kind == "post":
		site_item, arranged_item = factories.post(site_author), factories.post(arranged_author)
	else:
		site_item, arranged_item = factories.comment(site_author, factories.post(factories.user())), factories.comment(arranged_author, factories.post(factories.user()))

	for vote in votes:
		assert_status(as_user(site_voter).post(f"/vote/{kind}/{site_item['id']}/{vote}", headers=XHR), 204)
		factories.vote(arranged_voter, arranged_item, vote)

	counts = {"upvotes", "downvotes", "realupvotes"}
	assert {k: v for k, v in db.row(table, id=site_item["id"]).items() if k in counts} == {k: v for k, v in db.row(table, id=arranged_item["id"]).items() if k in counts}
	assert _without(_vote(vote_table, **{key: site_item["id"], "user_id": site_voter["id"]}), {"user_id", key}) == _without(_vote(vote_table, **{key: arranged_item["id"], "user_id": arranged_voter["id"]}), {"user_id", key})
	assert db.row("users", id=site_author["id"])["truescore"] == db.row("users", id=arranged_author["id"])["truescore"]


def test_a_factory_vote_by_a_shadowbanned_user_matches_one_cast_through_the_site():
	site_voter, arranged_voter = factories.user(shadowbanned="somemod"), factories.user(shadowbanned="somemod")
	site_item, arranged_item = factories.post(factories.user()), factories.post(factories.user())

	up = 1
	assert_status(as_user(site_voter).post(f"/vote/post/{site_item['id']}/{up}", headers=XHR), 204)
	factories.vote(arranged_voter, arranged_item, up)

	assert _without(db.row("submissions", id=site_item["id"]), _POST_IDENTITY | {"author_id"}) == _without(db.row("submissions", id=arranged_item["id"]), _POST_IDENTITY | {"author_id"})
	assert _without(_vote("votes", submission_id=site_item["id"], user_id=site_voter["id"]), {"user_id", "submission_id"}) == _without(_vote("votes", submission_id=arranged_item["id"], user_id=arranged_voter["id"]), {"user_id", "submission_id"})
	assert db.row("users", id=site_item["author_id"])["truescore"] == db.row("users", id=arranged_item["author_id"])["truescore"]
