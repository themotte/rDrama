'''
How the text people write is rendered: the "body" of comments, posts and messages, and a user's bio and friends list, are stored as written and rendered to HTML ("body_html", "bio_html", "friends_html"), which pages show. The rendering is compared here as an element tree: tag names, attributes and text, regardless of attribute order and of whitespace between elements.

Images are never shown inline: an image in Markdown (![text](address)) renders as a link to the image, its text being the image's text, or its address when that's empty.
'''
import pytest

from files.tests.spec.harness import *


def _rendered(body: str, author: dict | None = None) -> str:
	'''The rendering of `body` posted as a comment.'''
	author = author or factories.user()
	post = factories.post(factories.user())
	assert_status(as_user(author).post("/comment", {"parent_fullname": f"post_{post['id']}", "body": body}, headers=XHR), 200)
	[comment] = db.rows("comments", author_id=author["id"])
	return comment["body_html"]


EXTERNAL = {"target": "_blank", "rel": "nofollow noopener noreferrer"}


@pytest.mark.parametrize("body, html", [
	("![](https://i.imgur.com/i.png)", '<p><a href="https://i.imgur.com/i.png" target="_blank" rel="nofollow noopener noreferrer">https://i.imgur.com/i.png</a></p>'),
	("![](https://example.com/i.png)", '<p><a href="https://example.com/i.png" target="_blank" rel="nofollow noopener noreferrer">https://example.com/i.png</a></p>'),
	("![a picture](/images/x.webp)", '<p><a href="/images/x.webp">a picture</a></p>'),
	('![a picture](/images/x.webp "its title")', '<p><a href="/images/x.webp">a picture</a></p>'),
	("![a [b] c](/images/x.webp)", '<p><a href="/images/x.webp">a [b] c</a></p>'),
	("![pic][ref]\n\n[ref]: /images/x.webp", '<p><a href="/images/x.webp">pic</a></p>'),
	("\\![not](/images/x.webp)", '<p>!<a href="/images/x.webp">not</a></p>'),
	("`![x](/images/x.webp)`", "<p><code>![x](/images/x.webp)</code></p>"),
	("[![badge](/images/x.webp)](/leaderboard)", '<p><a href="/leaderboard">badge</a></p>'),
], ids=["embedding host", "other host", "on the site, with text", "with a title", "brackets in its text", "by reference", "escaped", "in code", "inside a link"])
def test_an_image_renders_as_a_link_to_it(body, html):
	assert_same_html(_rendered(body), html)
