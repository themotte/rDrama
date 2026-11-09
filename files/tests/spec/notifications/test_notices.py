'''
Notices: messages the site sends users in its own name, such as being followed, being added to a friends list, or an admin pinning one's post. A notice is stored as a comment without a post by the system account (account 1; AutoJanny, account 2, for automatic moderation), holding the notice's text ("body") and its rendering ("body_html"), and reaches each user it's for as a notification of that comment.

A notice is rendered as any written text is (spec/rendering/). A notice whose text is the same as an earlier notice's from the same account reuses that earlier comment, whatever its stored rendering. The notice telling users a post mentions them is one per post. Some notices may come to one user again (being unbanned, a post pinned): when the user already has the earlier comment, such a notice gets a comment of its own.
'''
from files.tests.spec.harness import *

SYSTEM = 1


def _notice(text, body_html="<p>stored by another implementation</p>"):
	return db.insert("comments", author_id=SYSTEM, parent_submission=None, body=text, body_html=body_html, level=1, distinguish_level=6, state_mod="VISIBLE", state_report="UNREPORTED", created_utc=1000, volunteer_janitor_badness=0.5)


def test_a_notice_reuses_an_earlier_one_with_the_same_text_whatever_its_rendering():
	follower, followed = factories.user(), factories.user()
	earlier = _notice(f"@{follower['username']} has followed you!")

	with db_diff() as d:
		as_user(follower).post(f"/follow/{followed['username']}", headers=XHR)

	assert d.inserted["notifications"] == [{"user_id": followed["id"], "comment_id": earlier["id"], "read": False, "created_datetimez": ANY}]
	assert "comments" not in d.inserted


def test_a_repeatable_notice_already_had_gets_a_comment_of_its_own():
	admin, author = factories.admin(2), factories.user()
	post = factories.post(author)
	as_user(admin).post(f"/sticky/{post['id']}", headers=XHR)
	as_user(admin).post(f"/unsticky/{post['id']}", headers=XHR)

	with db_diff() as d:
		as_user(admin).post(f"/sticky/{post['id']}", headers=XHR)

	[notice] = d.inserted["comments"]
	assert notice["body"] == f"@{admin['username']} has pinned your [post](/post/{post['id']})!"
	assert d.inserted["notifications"] == [{"user_id": author["id"], "comment_id": notice["id"], "read": False, "created_datetimez": ANY}]


def test_a_notice_is_rendered_as_written_text_is():
	author, follower = factories.user(), factories.user()
	db.insert("follows", user_id=follower["id"], target_id=author["id"])
	title = factories.unique("title")

	assert_status(as_user(author).post("/submit", {"title": f"**{title}**", "body": "x"}, headers=XHR), 200)

	[notice] = db.rows("comments", author_id=2)
	address = notice["body"].rsplit("](", 1)[1][:-1]
	assert notice["body"] == f"@{author['username']} has made a new post: [**{title}**]({address})"
	assert_same_html(notice["body_html"], f'<p><a href="/id/{author["id"]}">@{author["username"]}</a> has made a new post: <a href="{address}"><strong>{title}</strong></a></p>')
