'''
The vote counts the site keeps, and what they count:
- a post's or comment's upvotes and downvotes: its votes of +1 and -1 by users who aren't shadowbanned (its author's own vote included);
- a user's truescore: the sum of those votes on their posts and comments, other than their own.

Every way votes are cast keeps these exact.
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
				counted = {t: db.execute(f"SELECT count(*) FROM {votes} WHERE {key} = :id AND vote_type = :t AND {_BY_COUNTED_VOTER}", id=item["id"], t=t) for t in (1, -1)}
				assert (item["upvotes"], item["downvotes"]) == (counted[1], counted[-1]), f"{table} {item['id']}"
		truescore = db.execute(f"""
			SELECT coalesce(sum(v.vote_type), 0) FROM (
				SELECT vote_type, user_id, author_id FROM votes JOIN submissions s ON s.id = votes.submission_id
				UNION ALL
				SELECT vote_type, user_id, author_id FROM commentvotes JOIN comments c ON c.id = commentvotes.comment_id
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
