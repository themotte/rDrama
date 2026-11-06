'''
The vote counts the site keeps, and what they count:
- a post's or comment's upvotes and downvotes: its votes of +1 and -1 by users who aren't shadowbanned (its author's own vote included);
- a user's truescore: the sum of those votes on their posts and comments, other than their own.

Private messages are outside both: whatever votes they hold, their counts stay as they were sent, and votes on them move no truescore.

Every way votes are cast, and every way a user's shadowban changes, keeps these exact.
'''
import pytest

from files.tests.spec.harness import *

_BY_COUNTED_VOTER = "user_id IN (SELECT id FROM users WHERE shadowbanned IS NULL)"

_ITEMS = {"post": ("submissions", "votes", "submission_id"), "comment": ("comments", "commentvotes", "comment_id")}


def assert_vote_counts_exact(*users):
	'''The stored vote counts of every post and comment by `users`, and their truescores, equal a recount by their definitions.'''
	for user in users:
		for table, votes, key in _ITEMS.values():
			for item in db.rows(table, author_id=user["id"]):
				if table == "comments" and item["parent_submission"] is None: continue
				counted = {t: db.execute(f"SELECT count(*) FROM {votes} WHERE {key} = :id AND vote_type = :t AND {_BY_COUNTED_VOTER}", id=item["id"], t=t) for t in (1, -1)}
				assert (item["upvotes"], item["downvotes"]) == (counted[1], counted[-1]), f"{table} {item['id']}"
		truescore = db.execute(f"""
			SELECT coalesce(sum(v.vote_type), 0) FROM (
				SELECT vote_type, user_id, author_id FROM votes JOIN submissions s ON s.id = votes.submission_id
				UNION ALL
				SELECT vote_type, user_id, author_id FROM commentvotes JOIN comments c ON c.id = commentvotes.comment_id WHERE c.parent_submission IS NOT NULL
			) v WHERE v.author_id = :id AND v.user_id != :id AND {_BY_COUNTED_VOTER}
		""", id=user["id"])
		assert db.row("users", id=user["id"])["truescore"] == truescore, f"user {user['id']}"


@pytest.mark.parametrize("shadowbanned", [False, True])
def test_posting_and_commenting_keep_the_counts_exact(shadowbanned):
	author = factories.user(shadowbanned="somemod" if shadowbanned else None)
	client = as_user(author)
	assert_status(client.post("/submit", {"title": factories.unique("title"), "body": factories.unique("body")}), 200)
	post = db.rows("submissions", author_id=author["id"])[-1]

	assert_status(client.post("/comment", {"parent_fullname": f"post_{post['id']}", "body": factories.unique()}, headers=XHR), 200)

	assert_vote_counts_exact(author)


def test_voting_keeps_the_counts_exact():
	authors = [factories.user(), factories.user()]
	post = factories.post(authors[0])
	items = [("post", post), ("comment", factories.comment(authors[1], post)), ("comment", factories.comment(authors[0], post))]
	voters = [factories.user(), factories.user(shadowbanned="somemod"), authors[0], authors[1]]

	for round_votes in ([1, -1, 1, 0], [-1, -1, 0, 1], [0, 1, -1, -1]):
		for (kind, item), vote in zip(items + items[:1], round_votes):
			for voter in voters:
				assert_status(as_user(voter).post(f"/vote/{kind}/{item['id']}/{vote}", headers=XHR), 204)

	assert_vote_counts_exact(*authors)


# Shadowbans

def _voting_user(shadowbanned=False, **overrides):
	'''A user, with others, who has posted and commented and voted in every direction, alongside other voters; returns the user and every author involved.'''
	user = factories.user(shadowbanned="somemod" if shadowbanned else None, **overrides)
	others = [factories.user(), factories.user()]
	post = factories.post(user)
	comment = factories.comment(user, factories.post(others[0]))
	targets = [factories.post(others[0]), factories.post(others[1]), factories.comment(others[1], post), factories.comment(others[0], post), comment, post]
	# Their votes move one author's truescore by +1 and another's by -2
	for target, vote in zip(targets, [1, -1, -1, 0, 0, -1]):
		factories.vote(user, target, vote)
	for target in targets[:4]:
		factories.vote(others[0], target, 1)
		factories.vote(others[1], target, -1)
	for other in others:
		factories.vote(other, post, 1)
		factories.vote(other, comment, -1)
	message_id = db.execute("SELECT nextval('comments_id_seq')")
	message = db.insert("comments", id=message_id, author_id=others[0]["id"], sentto=user["id"], created_utc=1000, parent_submission=None, level=1, top_comment_id=message_id, body="hi", body_html="<p>hi</p>", volunteer_janitor_badness=0.5, state_mod="VISIBLE", state_report="UNREPORTED")
	db.insert("commentvotes", user_id=user["id"], comment_id=message["id"], vote_type=1, real=True)
	return user, [user, *others]


def _messages_unchanged(authors):
	return [(m["id"], m["upvotes"], m["downvotes"]) for a in authors for m in db.rows("comments", author_id=a["id"], parent_submission=None)]


def test_shadowbanning_uncounts_the_users_votes():
	user, authors = _voting_user()
	messages = _messages_unchanged(authors)

	assert_json_message(as_user(factories.admin(2)).post(f"/shadowban/{user['id']}", headers=XHR))

	assert_vote_counts_exact(*authors)
	assert _messages_unchanged(authors) == messages


def test_unshadowbanning_counts_the_users_votes_again():
	user, authors = _voting_user(shadowbanned=True)

	assert_json_message(as_user(factories.admin(2)).post(f"/unshadowban/{user['id']}", headers=XHR))

	assert_vote_counts_exact(*authors)


@pytest.mark.parametrize("path", ["shadowban", "unshadowban"])
def test_repeating_a_shadowban_change_counts_nothing_twice(path):
	user, authors = _voting_user(shadowbanned=path == "shadowban")

	assert_json_message(as_user(factories.admin(2)).post(f"/{path}/{user['id']}", headers=XHR))

	assert_vote_counts_exact(*authors)


def test_the_shadowban_for_ban_evasion_uncounts_the_users_votes():
	user, authors = _voting_user(ban_evade=1)

	assert_status(as_user(user).get("/"), 200)

	assert db.row("users", id=user["id"])["shadowbanned"] is not None
	assert_vote_counts_exact(*authors)


def test_reverting_shadowbans_counts_the_users_votes_again():
	(first, first_authors), (second, second_authors) = _voting_user(), _voting_user()
	factories.vote(first, db.rows("submissions", author_id=second["id"])[0], 1)
	factories.vote(second, db.rows("submissions", author_id=first["id"])[0], -1)
	moderator = factories.admin(2)
	client = as_user(moderator)
	for user in (first, second):
		assert_json_message(client.post(f"/shadowban/{user['id']}", headers=XHR))

	assert_json_message(as_user(factories.admin(3)).post(f"/@{moderator['username']}/revert_actions", headers=XHR))

	assert_vote_counts_exact(*first_authors, *second_authors)
