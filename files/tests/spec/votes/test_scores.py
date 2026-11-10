'''
How scores show. A post's or comment's score is its upvotes minus its downvotes. The post page (GET /post/<id>), post listings and the comments on a post page show each item's score, upvotes and downvotes, as do the JSON objects of posts ("score", "upvotes", "downvotes") and comments (see the comments area).

Scores are hidden from everyone while the item is younger than the configured score-hiding time (config.score_hiding_hours): the numbers are left out of pages and JSON alike.

A shadowbanned user's votes count for no one else, but they see them: the scores shown to them on pages, and in the JSON of a post (GET /post/<id>) or a comment (GET /comment/<id>, its embedded post included), add their own vote to the counted ones, wherever those pages and objects are loaded from (their notifications included).

A post's JSON tells the viewer their own vote on it ("voted": 1, 0 or -1; 0 also when they haven't voted).

Viewing a page never changes a score: a shadowbanned author viewing their own new comments, however often, leaves its votes as they are.
'''
import re
import time

import pytest

from files.tests.spec.harness import *

HIDING = config.score_hiding_hours() * 3600


def _scores():
	'''Vote counts unlikely to appear anywhere else in a page, with the score distinct from both.'''
	n = int(re.sub(r"\D", "", factories.unique()))
	ups, downs = 60_600_000 + 3 * n, 20_200_000 + n
	return ups, downs, ups - downs


def _old():
	return int(time.time()) - HIDING - 60


def _post_page(item_kind, ups, downs, created_utc):
	'''A post page showing a post or a comment with the given counts.'''
	if item_kind == "post":
		post = factories.post(factories.user(), upvotes=ups, downvotes=downs, created_utc=created_utc)
	else:
		post = factories.post(factories.user())
		factories.comment(factories.user(), post, upvotes=ups, downvotes=downs, created_utc=created_utc)
	return f"/post/{post['id']}"


@pytest.mark.parametrize("item_kind", ["post", "comment"])
def test_the_post_page_shows_scores(item_kind):
	ups, downs, score = _scores()
	url = _post_page(item_kind, ups, downs, _old())

	r = as_user(factories.user()).get(url)

	assert_status(r, 200)
	for number in (ups, downs, score):
		assert_in_payload(r, str(number))


@pytest.mark.parametrize("item_kind", ["post", "comment"])
def test_the_post_page_hides_scores_of_items_younger_than_the_hiding_time(item_kind):
	ups, downs, score = _scores()
	url = _post_page(item_kind, ups, downs, int(time.time()) - HIDING + 600)

	r = as_user(factories.user()).get(url)

	assert_status(r, 200)
	for number in (ups, downs, score):
		assert_not_in_payload(r, str(number))


@pytest.mark.parametrize("age,shown", [(HIDING + 60, True), (HIDING - 600, False)])
def test_post_listings_show_scores_after_the_hiding_time(age, shown):
	ups, downs, score = _scores()
	author = factories.user()
	factories.post(author, upvotes=ups, downvotes=downs, created_utc=int(time.time()) - age)

	r = as_user(factories.user()).get(f"/@{author['username']}/posts")

	assert_status(r, 200)
	for number in (ups, downs, score):
		(assert_in_payload if shown else assert_not_in_payload)(r, str(number))


def test_post_json_has_the_scores():
	ups, downs, score = _scores()
	post = factories.post(factories.user(), upvotes=ups, downvotes=downs, created_utc=_old())

	r = as_api(factories.api_token(factories.user())).get(f"/post/{post['id']}")

	assert_status(r, 200)
	assert (r.json["score"], r.json["upvotes"], r.json["downvotes"]) == (score, ups, downs)


def test_post_json_leaves_out_scores_of_young_posts():
	post = factories.post(factories.user(), created_utc=int(time.time()) - HIDING + 600)

	r = as_api(factories.api_token(factories.user())).get(f"/post/{post['id']}")

	assert_status(r, 200)
	assert not {"score", "upvotes", "downvotes"} & set(r.json)


@pytest.mark.parametrize("vote", [1, 0, -1, None])
def test_post_json_tells_the_viewers_own_vote(vote):
	viewer = factories.user()
	post = factories.post(factories.user())
	if vote is not None:
		factories.vote(viewer, post, vote)

	r = as_api(factories.api_token(viewer)).get(f"/post/{post['id']}")

	assert_status(r, 200)
	assert r.json["voted"] == (vote or 0)


def test_a_shadowbanned_author_viewing_their_new_comment_changes_no_score():
	author = factories.user(shadowbanned="somemod")
	post = factories.post(factories.user())
	factories.comment(author, post, created_utc=int(time.time()) - 15 * 60)
	client = as_user(author)

	with db_diff() as d:
		for _ in range(20):
			assert_status(client.get(f"/post/{post['id']}"), 200)

	d.assert_exactly(updated={"submissions": {post["id"]: {"views": ANY}}})


# A shadowbanned voter's own votes

def _voted_on(kind, voter, vote):
	'''An old post, or an old comment on one, that `voter` voted `vote` on, with improbable counted numbers; returns it, its post and the counted (ups, downs).'''
	post = factories.post(factories.user(), created_utc=_old())
	item = post if kind == "post" else factories.comment(factories.user(), post, created_utc=_old())
	factories.vote(voter, item, vote)
	ups, downs, _ = _scores()
	db.update("submissions" if kind == "post" else "comments", {"id": item["id"]}, upvotes=ups, downvotes=downs)
	return item, post, (ups, downs)


def _shown(ups, downs, vote):
	ups, downs = ups + (vote == 1), downs + (vote == -1)
	return ups, downs, ups - downs


@pytest.mark.parametrize("kind", ["post", "comment"])
@pytest.mark.parametrize("vote", [1, -1])
def test_a_shadowbanned_voter_sees_their_own_vote_on_the_post_page(kind, vote):
	voter = factories.user(shadowbanned="somemod")
	_, post, (ups, downs) = _voted_on(kind, voter, vote)

	r = as_user(voter).get(f"/post/{post['id']}")

	assert_status(r, 200)
	for number in _shown(ups, downs, vote):
		assert_in_payload(r, str(number))


@pytest.mark.parametrize("kind", ["post", "comment"])
def test_others_see_only_the_counted_votes(kind):
	voter = factories.user(shadowbanned="somemod")
	_, post, (ups, downs) = _voted_on(kind, voter, 1)

	r = as_user(factories.user()).get(f"/post/{post['id']}")

	assert_status(r, 200)
	assert_in_payload(r, str(ups))
	assert_not_in_payload(r, str(ups + 1))


def test_a_shadowbanned_voter_sees_their_own_vote_in_post_listings():
	voter = factories.user(shadowbanned="somemod")
	post, _, (ups, downs) = _voted_on("post", voter, 1)
	author = db.row("users", id=post["author_id"])

	r = as_user(voter).get(f"/@{author['username']}/posts")

	assert_status(r, 200)
	for number in _shown(ups, downs, 1):
		assert_in_payload(r, str(number))


def test_a_shadowbanned_voter_sees_their_own_vote_in_post_json():
	voter = factories.user(shadowbanned="somemod")
	post, _, (ups, downs) = _voted_on("post", voter, -1)

	r = as_api(factories.api_token(voter)).get(f"/post/{post['id']}")

	assert_status(r, 200)
	assert (r.json["upvotes"], r.json["downvotes"], r.json["score"]) == _shown(ups, downs, -1)


def test_a_shadowbanned_voter_sees_their_own_vote_in_comment_json():
	voter = factories.user(shadowbanned="somemod")
	comment, _, (ups, downs) = _voted_on("comment", voter, 1)

	r = as_api(factories.api_token(voter)).get(f"/comment/{comment['id']}")

	assert_status(r, 200)
	assert (r.json["upvotes"], r.json["downvotes"], r.json["score"]) == _shown(ups, downs, 1)


def test_a_shadowbanned_voter_sees_their_own_vote_on_a_comments_embedded_post():
	voter = factories.user(shadowbanned="somemod")
	post, _, (ups, downs) = _voted_on("post", voter, 1)
	comment = factories.comment(factories.user(), post)

	r = as_api(factories.api_token(voter)).get(f"/comment/{comment['id']}")

	assert_status(r, 200)
	assert (r.json["post"]["upvotes"], r.json["post"]["downvotes"], r.json["post"]["score"]) == _shown(ups, downs, 1)


def test_a_shadowbanned_voter_sees_their_own_vote_on_comments_in_their_notifications():
	voter = factories.user(shadowbanned="somemod")
	comment, _, (ups, downs) = _voted_on("comment", voter, 1)
	db.insert("notifications", user_id=voter["id"], comment_id=comment["id"], read=False)

	r = as_user(voter).get("/notifications")

	assert_status(r, 200)
	for number in _shown(ups, downs, 1):
		assert_in_payload(r, str(number))
