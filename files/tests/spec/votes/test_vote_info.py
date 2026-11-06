'''
The vote-info page, for admins of level 3 and up: GET /votes shows a form, and GET /votes?link=post_<id> or link=comment_<id> shows the item's author and who voted on it: its upvoters, then its downvoters, each in the order they first voted. Voters whose vote is 0 aren't listed.

The page of an anonymous post or comment is refused (403) to every admin, as it would name the author.

Posts and comments link to their vote-info page (/votes?link=post_<id> or comment_<id>) where the viewer may open it, and not on anonymous items. A link naming neither a post nor a comment is refused with 400; one naming an unknown post or comment, or one whose id isn't an id, is 404.

Anonymous visitors are sent to log in; users below level 3 and API clients are refused (403).
'''
import pytest

from files.tests.spec.harness import *


def _item(kind, author, **overrides):
	if kind == "post":
		return factories.post(author, **overrides)
	return factories.comment(author, factories.post(factories.user(), **overrides), **overrides)


def _voted_at(kind, voter, item, minutes_ago):
	table, key = ("votes", "submission_id") if kind == "post" else ("commentvotes", "comment_id")
	db.execute(f"UPDATE {table} SET created_datetimez = now() - make_interval(mins => :m) WHERE user_id = :user AND {key} = :item", m=minutes_ago, user=voter["id"], item=item["id"])


def test_the_form_shows_without_a_link():
	assert_html(as_user(factories.admin(3)).get("/votes"), 200)


@pytest.mark.parametrize("kind", ["post", "comment"])
def test_the_page_lists_upvoters_then_downvoters_in_the_order_they_voted(kind):
	author = factories.user()
	item = _item(kind, author)
	early_up, late_up, early_down, late_down, cleared = (factories.user() for _ in range(5))
	for voter, vote, minutes_ago in [(late_up, 1, 10), (early_up, 1, 30), (late_down, -1, 5), (early_down, -1, 20), (cleared, 0, 40)]:
		factories.vote(voter, item, vote)
		_voted_at(kind, voter, item, minutes_ago)
	_voted_at(kind, author, item, 60)

	r = as_user(factories.admin(3)).get("/votes", params={"link": f"{kind}_{item['id']}"})

	assert_html(r, 200)
	assert_not_in_payload(r, cleared["username"])
	# The author is named above the lists too, so their place in the list is their last mention
	positions = [r.text.rindex(user["username"]) for user in (author, early_up, late_up, early_down, late_down)]
	assert positions == sorted(positions)


@pytest.mark.parametrize("kind", ["post", "comment"])
def test_anonymous_items_are_refused(kind):
	item = _item(kind, factories.user(), ghost=True)

	r = as_user(factories.admin(3)).get("/votes", params={"link": f"{kind}_{item['id']}"})

	assert_status(r, 403)


def _page_with(kind, **overrides):
	post = factories.post(factories.user(), **overrides)
	item = post if kind == "post" else factories.comment(factories.user(), post)
	return f"/post/{post['id']}", f"/votes?link={kind}_{item['id']}"


@pytest.mark.parametrize("kind", ["post", "comment"])
def test_items_link_to_their_vote_info_for_level_3_admins(kind):
	page, link = _page_with(kind)

	r = as_user(factories.admin(3)).get(page)

	assert_status(r, 200)
	assert_in_payload(r, link)


@pytest.mark.parametrize("kind", ["post", "comment"])
@pytest.mark.parametrize("level", [0, 1, 2])
def test_items_dont_link_to_their_vote_info_below_level_3(kind, level):
	page, link = _page_with(kind)

	r = as_user(factories.admin(level)).get(page)

	assert_status(r, 200)
	assert_not_in_payload(r, link)


@pytest.mark.parametrize("kind", ["post", "comment"])
def test_anonymous_items_dont_link_to_their_vote_info(kind):
	page, link = _page_with(kind, ghost=True)

	r = as_user(factories.admin(3)).get(page)

	assert_status(r, 200)
	assert_not_in_payload(r, link)


def test_a_link_naming_no_post_or_comment_is_refused():
	r = as_user(factories.admin(3)).get("/votes", params={"link": factories.unique()})

	assert_status(r, 400)


@pytest.mark.parametrize("kind", ["post", "comment"])
@pytest.mark.parametrize("which", ["unknown", "not an id"])
def test_links_to_unknown_items_are_not_found(kind, which):
	table = "submissions" if kind == "post" else "comments"
	item_id = db.execute(f"SELECT nextval('{table}_id_seq')") if which == "unknown" else "abc"

	r = as_user(factories.admin(3)).get("/votes", params={"link": f"{kind}_{item_id}"})

	assert_status(r, 404)


def test_anonymous_visitors_are_sent_to_log_in():
	assert_login_redirect(anon().get("/votes"), "/votes")


@pytest.mark.parametrize("level", [0, 1, 2])
def test_users_below_level_3_are_refused(level):
	assert_status(as_user(factories.admin(level)).get("/votes"), 403)


def test_api_clients_are_refused():
	assert_status(as_api(factories.api_token(factories.admin(3))).get("/votes"), 403)
