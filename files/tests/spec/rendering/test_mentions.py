'''
Mentions in rendered text (see test_text.py): "@<username>" at the start of the text or of a paragraph, or after whitespace, naming an existing user by their username or their original one, in any letter case, renders as a link to /id/<their id> reading "@<their username>". Every mention of them is linked. Not inside code, and not right after another character (as in an email address).

A mention isn't linked when the writer blocks the mentioned user or is blocked by them, unless the writer is an admin of level 2 or higher.

Text mentioning more than 100 existing users is refused with 400; names of no user don't count.

Who a mention notifies is decided on the written text instead (spec/comments/test_create.py), so a name a rendering leaves unlinked, in code for instance, may still notify.
'''
import pytest

from files.tests.spec.harness import *


def _rendered(body: str, author: dict | None = None):
	'''The response to posting `body` as a comment, and its rendering.'''
	author = author or factories.user()
	post = factories.post(factories.user())
	r = as_user(author).post("/comment", {"parent_fullname": f"post_{post['id']}", "body": body}, headers=XHR)
	comments = db.rows("comments", author_id=author["id"])
	return r, comments[0]["body_html"] if comments else None


def _mention(user) -> str:
	return f'<a href="/id/{user["id"]}">@{user["username"]}</a>'


@pytest.mark.parametrize("written, html", [
	("@{name} hi", "<p>{link} hi</p>"),
	("hi @{name}", "<p>hi {link}</p>"),
	("one\n\n@{name}", "<p>one</p><p>{link}</p>"),
	("@{upper} and @{name}", "<p>{link} and {link}</p>"),
	("mail a@{name}", "<p>mail a@{name}</p>"),
	("`@{name}`", "<p><code>@{name}</code></p>"),
], ids=["start", "after a space", "start of a paragraph", "any case, every time", "after a character", "in code"])
def test_a_mention_links_to_the_user(written, html):
	user = factories.user()
	name = user["username"]

	r, rendered = _rendered(written.format(name=name, upper=name.upper()))

	assert_status(r, 200)
	assert_same_html(rendered, html.format(name=name, link=_mention(user)))


def test_a_mention_by_original_username_links_to_the_user_by_their_current_one():
	original = factories.unique("old")
	user = factories.user(original_username=original)

	_, rendered = _rendered(f"@{original}")

	assert_same_html(rendered, f"<p>{_mention(user)}</p>")


def test_a_mention_of_no_one_stays_text():
	name = factories.unique("nobody")

	_, rendered = _rendered(f"@{name}")

	assert_same_html(rendered, f"<p>@{name}</p>")


@pytest.mark.parametrize("blocker", ["writer", "mentioned"])
@pytest.mark.parametrize("writer_level, linked", [(0, False), (1, False), (2, True)])
def test_a_block_either_way_leaves_a_mention_unlinked_except_from_admins(blocker, writer_level, linked):
	writer, mentioned = factories.admin(writer_level), factories.user()
	db.insert("userblocks", **({"user_id": writer["id"], "target_id": mentioned["id"]} if blocker == "writer" else {"user_id": mentioned["id"], "target_id": writer["id"]}))

	_, rendered = _rendered(f"@{mentioned['username']}", author=writer)

	assert_same_html(rendered, f"<p>{_mention(mentioned) if linked else '@' + mentioned['username']}</p>")


@pytest.mark.parametrize("count, status", [(100, 200), (101, 400)])
def test_text_may_mention_up_to_100_users(count, status):
	users = [factories.user() for _ in range(count)]
	author, post = factories.user(), factories.post(factories.user())
	body = " ".join(f"@{u['username']}" for u in users) + " @" + factories.unique("nobody")

	with db_diff() as d:
		r = as_user(author).post("/comment", {"parent_fullname": f"post_{post['id']}", "body": body}, headers=XHR)

	assert_status(r, status)
	if status == 400:
		d.assert_exactly()
