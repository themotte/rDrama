'''
Voting: POST /vote/post/<post id>/<vote> and POST /vote/comment/<comment id>/<vote>, where <vote> is "1" (up), "-1" (down) or "0" (no vote). The answer is 204 with an empty body.

Each user has at most one vote on each post and comment. Voting sets it: the first vote stores it, a later one changes it, and "0" keeps the vote as a vote of 0. Sending the vote already set changes nothing. Posting and commenting cast the author's own upvote.

A vote stores whether it is "real": the voter wasn't shadowbanned when it was set.

After a change, the item's upvotes and downvotes are its +1 and -1 votes, and its "realupvotes" are its real +1 votes. The author's truescore moves by the change (from the old vote to the new one), unless the voter is the author.

Refused, changing nothing, in this order: 401 for anonymous users; 403 for API clients; 403 for permanently suspended users (temporarily suspended users vote as anyone else); 400 for any other <vote>; 404 for an unknown item or an id that isn't one, and for a draft, or a comment on a draft, that the voter can't see (only its author and admins of level 2 and up see a draft), and for every private message, which have no scores; 403 for an item hidden from the voter, which shows them only a placeholder (removed, held for review, deleted by its author, or by a shadowbanned user; its author and the admins who see it vote on it); 403 when the voter blocks the item's author, even where they still see it (an official post; an admin). The 18+ gate doesn't stop voting.
'''
import time

import pytest

from files.tests.spec.harness import *

KINDS = ["post", "comment"]
_TABLES = {"post": ("submissions", "votes", "submission_id"), "comment": ("comments", "commentvotes", "comment_id")}


def _item(kind, author, **overrides):
	if kind == "post":
		return factories.post(author, **overrides)
	return factories.comment(author, factories.post(factories.user()), **overrides)


def _vote(client, kind, item, vote, headers=XHR):
	return client.post(f"/vote/{kind}/{item['id']}/{vote}", headers=headers)


def _vote_row(kind, voter, item, vote_type, real=True):
	_, _, key = _TABLES[kind]
	return {"user_id": voter["id"], key: item["id"], "vote_type": vote_type, "real": real}


def _assert_voted(r):
	assert_status(r, 204)
	assert r.body == b""


# Voting

@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("vote,changed", [(1, {"upvotes": 2, "realupvotes": 2}), (-1, {"downvotes": 1})])
def test_a_first_vote_is_stored_and_counted(kind, vote, changed):
	author, voter = factories.user(), factories.user()
	item = _item(kind, author)
	table, votes, _ = _TABLES[kind]
	client = as_user(voter)

	with db_diff() as d:
		r = _vote(client, kind, item, vote)

	_assert_voted(r)
	d.assert_exactly(
		inserted={votes: [_vote_row(kind, voter, item, vote)]},
		updated={
			table: {item["id"]: changed},
			"users": {author["id"]: {"truescore": vote}},
		},
	)


@pytest.mark.parametrize("kind", KINDS)
def test_changing_a_vote_moves_the_counts_and_truescore_by_the_change(kind):
	author, voter = factories.user(), factories.user()
	item = factories.vote(voter, _item(kind, author), 1)
	table, votes, key = _TABLES[kind]
	client = as_user(voter)

	with db_diff() as d:
		r = _vote(client, kind, item, -1)

	_assert_voted(r)
	d.assert_exactly(updated={
		votes: {(item["id"], voter["id"]): {"vote_type": -1}},
		table: {item["id"]: {"upvotes": 1, "downvotes": 1, "realupvotes": 1}},
		"users": {author["id"]: {"truescore": -1}},
	})


@pytest.mark.parametrize("kind", KINDS)
def test_clearing_a_vote_keeps_it_as_a_vote_of_0(kind):
	author, voter = factories.user(), factories.user()
	item = factories.vote(voter, _item(kind, author), -1)
	table, votes, _ = _TABLES[kind]
	client = as_user(voter)

	with db_diff() as d:
		r = _vote(client, kind, item, 0)

	_assert_voted(r)
	d.assert_exactly(updated={
		votes: {(item["id"], voter["id"]): {"vote_type": 0}},
		table: {item["id"]: {"downvotes": 0}},
		"users": {author["id"]: {"truescore": 0}},
	})


@pytest.mark.parametrize("kind", KINDS)
def test_the_authors_own_vote_moves_the_counts_but_not_their_truescore(kind):
	author = factories.user()
	item = _item(kind, author)
	table, votes, _ = _TABLES[kind]
	client = as_user(author)

	with db_diff() as d:
		r = _vote(client, kind, item, -1)

	_assert_voted(r)
	d.assert_exactly(updated={
		votes: {(item["id"], author["id"]): {"vote_type": -1}},
		table: {item["id"]: {"upvotes": 0, "downvotes": 1, "realupvotes": 0}},
	})


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("vote", [1, 0, -1])
def test_sending_the_vote_already_set_changes_nothing(kind, vote):
	voter = factories.user()
	item = factories.vote(voter, _item(kind, factories.user()), vote)
	client = as_user(voter)

	with db_diff() as d:
		r = _vote(client, kind, item, vote)

	_assert_voted(r)
	d.assert_exactly()


@pytest.mark.parametrize("kind", KINDS)
def test_sending_the_vote_already_set_keeps_whether_it_is_real(kind):
	voter = factories.user()
	item = factories.vote(voter, _item(kind, factories.user()), 1)
	db.update("users", {"id": voter["id"]}, shadowbanned="somemod")
	client = as_user(voter)

	with db_diff() as d:
		r = _vote(client, kind, item, 1)

	_assert_voted(r)
	d.assert_exactly()


@pytest.mark.parametrize("kind", KINDS)
def test_realupvotes_count_only_real_upvotes(kind):
	author, voter = factories.user(), factories.user()
	unreal = factories.user(shadowbanned="somemod")
	item = factories.vote(unreal, _item(kind, author), 1)
	table, _, _ = _TABLES[kind]

	_assert_voted(_vote(as_user(voter), kind, item, 1))

	assert db.row(table, id=item["id"])["realupvotes"] == 2


@pytest.mark.parametrize("ban", ["temporary", "expired"])
@pytest.mark.parametrize("kind", KINDS)
def test_users_not_permanently_suspended_vote(kind, ban):
	voter = factories.user(is_banned=factories.admin(2)["id"], unban_utc=int(time.time()) + (86400 if ban == "temporary" else -60))
	item = _item(kind, factories.user())
	_, votes, _ = _TABLES[kind]

	_assert_voted(_vote(as_user(voter), kind, item, 1))

	assert db.rows(votes, user_id=voter["id"]) != []


@pytest.mark.parametrize("kind", KINDS)
def test_voting_on_content_by_a_user_who_blocks_the_voter_is_allowed(kind):
	author, voter = factories.user(), factories.user()
	db.insert("userblocks", user_id=author["id"], target_id=voter["id"])

	_assert_voted(_vote(as_user(voter), kind, _item(kind, author), 1))


# Refusals

@pytest.mark.parametrize("kind", KINDS)
def test_anonymous_scripts_are_unauthorized(kind):
	item = _item(kind, factories.user())

	with db_diff() as d:
		r = _vote(anon(), kind, item, 1)

	assert_api_unauthorized(r)
	d.assert_exactly()


@pytest.mark.parametrize("kind", KINDS)
def test_api_clients_cant_vote(kind):
	voter = factories.user()
	item = _item(kind, factories.user())
	client = as_api(factories.api_token(voter))

	with db_diff() as d:
		r = _vote(client, kind, item, 1)

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("kind", KINDS)
def test_permanently_suspended_users_cant_vote(kind):
	voter = factories.user(is_banned=factories.admin(2)["id"], unban_utc=0)
	item = _item(kind, factories.user())
	client = as_user(voter)

	with db_diff() as d:
		r = _vote(client, kind, item, 1)

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("vote", ["2", "-2", "+1", "01", "up", "1.0"])
def test_other_votes_are_refused(kind, vote):
	item = _item(kind, factories.user())
	client = as_user(factories.user())

	with db_diff() as d:
		r = _vote(client, kind, item, vote)

	assert_status(r, 400)
	d.assert_exactly()


@pytest.mark.parametrize("kind", KINDS)
def test_a_bad_vote_is_refused_before_the_item_is_looked_up(kind):
	r = _vote(as_user(factories.user()), kind, {"id": "abc"}, "2")

	assert_status(r, 400)


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("which", ["unknown", "not an id"])
def test_unknown_items_are_not_found(kind, which):
	table, _, _ = _TABLES[kind]
	item_id = db.execute(f"SELECT nextval('{table}_id_seq')") if which == "unknown" else "abc"

	r = _vote(as_user(factories.user()), kind, {"id": item_id}, 1)

	assert_status(r, 404)


@pytest.mark.parametrize("kind", KINDS)
def test_voting_on_content_by_a_user_the_voter_blocks_is_refused(kind):
	author, voter = factories.user(), factories.user()
	db.insert("userblocks", user_id=voter["id"], target_id=author["id"])
	item = _item(kind, author)
	client = as_user(voter)

	with db_diff() as d:
		r = _vote(client, kind, item, 1)

	assert_status(r, 403)
	d.assert_exactly()


# Drafts

def _on_draft(kind, author):
	draft = factories.post(author, private=True)
	return draft if kind == "post" else factories.comment(author, draft)


@pytest.mark.parametrize("kind", KINDS)
def test_drafts_the_voter_cant_see_are_not_found(kind):
	item = _on_draft(kind, factories.user())
	client = as_user(factories.user())

	with db_diff() as d:
		r = _vote(client, kind, item, 1)

	assert_status(r, 404)
	d.assert_exactly()


@pytest.mark.parametrize("kind", KINDS)
def test_a_blocked_authors_draft_is_not_found_rather_than_refused(kind):
	author, voter = factories.user(), factories.user()
	db.insert("userblocks", user_id=voter["id"], target_id=author["id"])

	r = _vote(as_user(voter), kind, _on_draft(kind, author), 1)

	assert_status(r, 404)


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("who", ["author", "admin"])
def test_those_who_see_a_draft_vote_on_it(kind, who):
	author = factories.user()
	voter = author if who == "author" else factories.admin(2)

	_assert_voted(_vote(as_user(voter), kind, _on_draft(kind, author), -1))


# Private messages

def _message(sender, recipient):
	message_id = db.execute("SELECT nextval('comments_id_seq')")
	return db.insert("comments", id=message_id, author_id=sender["id"], sentto=recipient["id"], created_utc=int(time.time()), parent_submission=None, level=1, top_comment_id=message_id, body="hi", body_html="<p>hi</p>", volunteer_janitor_badness=0.5, state_mod="VISIBLE", state_report="UNREPORTED")


@pytest.mark.parametrize("who", ["sender", "recipient", "admin", "other"])
def test_private_messages_are_not_found(who):
	sender, recipient = factories.user(), factories.user()
	message = _message(sender, recipient)
	voter = {"sender": sender, "recipient": recipient, "admin": factories.admin(3), "other": factories.user()}[who]
	client = as_user(voter)

	with db_diff() as d:
		r = _vote(client, "comment", message, 1)

	assert_status(r, 404)
	d.assert_exactly()


# Hidden items

HIDDEN = {
	"removed": lambda: {"state_mod": "REMOVED", "state_mod_set_by": "somemod"},
	"held for review": lambda: {"state_mod": "FILTERED"},
	"deleted": lambda: {"state_user_deleted_utc": "2020-01-01T00:00:00Z"},
}


def _hidden(kind, state, author=None):
	author = author or (factories.user(shadowbanned="somemod") if state == "by a shadowbanned user" else factories.user())
	return author, _item(kind, author, **({} if state == "by a shadowbanned user" else HIDDEN[state]()))


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("state", [*HIDDEN, "by a shadowbanned user"])
def test_items_hidden_from_the_voter_are_refused(kind, state):
	_, item = _hidden(kind, state)
	client = as_user(factories.user())

	with db_diff() as d:
		r = _vote(client, kind, item, 1)

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("state", [*HIDDEN, "by a shadowbanned user"])
@pytest.mark.parametrize("who", ["author", "admin"])
def test_those_who_see_a_hidden_item_vote_on_it(kind, state, who):
	author, item = _hidden(kind, state)
	voter = author if who == "author" else factories.admin(2)

	_assert_voted(_vote(as_user(voter), kind, item, -1))


@pytest.mark.parametrize("case", ["official post", "admin"])
def test_voting_on_a_blocked_authors_item_the_voter_still_sees_is_refused(case):
	author = factories.user()
	voter = factories.admin(2) if case == "admin" else factories.user()
	db.insert("userblocks", user_id=voter["id"], target_id=author["id"])
	post = factories.post(author, distinguish_level=1 if case == "official post" else 0)

	assert_status(_vote(as_user(voter), "post", post, 1), 403)


@pytest.mark.parametrize("kind", KINDS)
def test_the_18_plus_gate_doesnt_stop_voting(kind):
	item = _item(kind, factories.user(), over_18=True)

	_assert_voted(_vote(as_user(factories.user()), kind, item, 1))
