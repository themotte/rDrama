'''
How the text people write is rendered: the "body" of comments, posts and messages, and a user's bio and friends list, are stored as written (a body trimmed, its line ends made "\n" and attached images' links added, as test_create.py and test_submit.py say) and rendered to HTML ("body_html", "bio_html", "friends_html"), which pages show. The rendering is compared here as an element tree: tag names, attributes and text, regardless of attribute order and of whitespace between elements. The data the rules refer to is in the tables below (KEPT_ELEMENTS, DROPPED_ELEMENTS, TOP_LEVEL_DOMAINS, REWRITES), each entry checked.

In order:
- Invisible characters are removed: zero-width spaces, left-to-right and right-to-left marks, byte-order marks and U+1242A.
- Images are never shown inline: an image in Markdown (![text](address)) renders as a link to the image, its text being the image's text, or its address when that's empty. Inside a link, it renders as just that text.
- The text is Markdown (CommonMark, with tables): paragraphs, emphasis, headings, block quotes, lists, code spans and blocks (a fenced block's language is dropped), rules, hard line breaks, links and autolinks, and raw HTML.
- The site's conventions below apply within runs of text, outside code, links and web addresses, and never to markup: text between single or double tildes (~like this~, ~~or this~~) is struck through (<del>), and ||text|| becomes a spoiler (<spoiler>).
- Mentions of users (test_mentions.py) become links to them.
- Likewise, "/r/<name>" and "/u/<name>" (3 to 25 letters, digits, "_" or "-", not followed by more) at the start of a run of text or after whitespace link to Reddit (old.reddit.com), and "/h/<name>" to that path on the site.
- A link whose text is itself a web address shows its real address instead.
- Only the elements in KEPT_ELEMENTS are kept: other elements are dropped but their text stays (DROPPED_ELEMENTS). Only these attributes are kept: "style" on any element, keeping only the CSS properties "color", "background-color", "font-weight" and "text-align"; on "a", "href", "target" only as "_blank" and "rel" only as "nofollow noopener noreferrer"; on "span", "title", "alt" and "data-bs-toggle" only as "tooltip". A link keeps its address unless it has a scheme other than http or https (in any letter case).
- Web addresses in the text become links (not inside code) when their host name's last label is one of TOP_LEVEL_DOMAINS, with http:// or https:// or bare (linked with http://). Links leaving the site open in a new tab (target "_blank", rel "nofollow noopener noreferrer"); links to the site's own pages (an address starting with "/", or the site's own address) aren't given them, but keep them if written with them.
- Every link's address is then rewritten by the replacements in REWRITES, in that order, wherever they occur in it; then a YouTube video's address takes its start time as "&t=" rather than "?t=", and query parameters "utm_<word>=<value>" are removed; a link showing its own address (with or without its scheme) shows it rewritten too. Text that isn't a link's address, code included, is left as written.

Text linking to a banned domain is refused with 403: a link's host, any of the host's parent domains, or its host and path, being listed in "banneddomains".
'''
import pytest

from files.tests.spec.harness import *

EXTERNAL = 'target="_blank" rel="nofollow noopener noreferrer"'


def _rendered(body: str, author: dict | None = None) -> str:
	'''The rendering of `body` posted as a comment.'''
	author = author or factories.user()
	post = factories.post(factories.user())
	assert_status(_comment(author, post, body), 200)
	[comment] = db.rows("comments", author_id=author["id"])
	return comment["body_html"]


def _comment(author, post, body):
	return as_user(author).post("/comment", {"parent_fullname": f"post_{post['id']}", "body": body}, headers=XHR)


def _link(address, text=None):
	return f'<a href="{address}" {EXTERNAL}>{address if text is None else text}</a>'


@pytest.mark.parametrize("body, html", [
	("plain text", "<p>plain text</p>"),
	("two\nlines", "<p>two lines</p>"),
	("one\n\ntwo", "<p>one</p><p>two</p>"),
	("line  \nbreak", "<p>line<br>break</p>"),
	("*em* **strong** ***both***", "<p><em>em</em> <strong>strong</strong> <em><strong>both</strong></em></p>"),
	("# h1\n## h2\n###### h6", "<h1>h1</h1><h2>h2</h2><h6>h6</h6>"),
	("> quote", "<blockquote><p>quote</p></blockquote>"),
	("- a\n- b", "<ul><li>a</li><li>b</li></ul>"),
	("1. a\n2. b", "<ol><li>a</li><li>b</li></ol>"),
	("`code` here", "<p><code>code</code> here</p>"),
	("```python\nx = 1\n```", "<pre><code>x = 1\n</code></pre>"),
	("---", "<hr>"),
	("| a | b |\n|---|---|\n| 1 | 2 |", "<table><thead><tr><th>a</th><th>b</th></tr></thead><tbody><tr><td>1</td><td>2</td></tr></tbody></table>"),
	("&amp; &lt; & <", "<p>&amp; &lt; &amp; &lt;</p>"),
], ids=["paragraph", "soft break", "paragraphs", "hard break", "emphasis", "headings", "quote", "list", "numbered list", "code span", "code block", "rule", "table", "escapes"])
def test_markdown(body, html):
	assert_same_html(_rendered(body), html)


@pytest.mark.parametrize("body, html", [
	("![](https://i.imgur.com/i.png)", f'<p>{_link("https://i.imgur.com/i.png")}</p>'),
	("![](https://example.com/i.png)", f'<p>{_link("https://example.com/i.png")}</p>'),
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


@pytest.mark.parametrize("body, html", [
	("<sub>sub</sub> <sup>sup</sup> <ruby>漢<rp>(</rp><rt>kan</rt><rp>)</rp></ruby>", "<p><sub>sub</sub> <sup>sup</sup> <ruby>漢<rp>(</rp><rt>kan</rt><rp>)</rp></ruby></p>"),
	("<table><tr><td>t</td></tr></table>", "<table><tbody><tr><td>t</td></tr></tbody></table>"),
	("<script>alert(1)</script>", "alert(1)"),
	("<div>div</div>", "div"),
	("<style>p{}</style>", "p{}"),
	('<iframe src="https://example.com"></iframe>', ""),
	('<img src="https://example.com/y.png">', ""),
	("<b onclick='x'>b</b>", "<p><b>b</b></p>"),
	('<p class="c" id="i" title="t">p</p>', "<p>p</p>"),
	('<span title="t" data-bs-toggle="tooltip" class="c" alt="a">s</span>', '<p><span title="t" data-bs-toggle="tooltip" alt="a">s</span></p>'),
	('<span data-bs-toggle="popover">s</span>', "<p><span>s</span></p>"),
	('<p style="color: red; position: absolute; background-color: blue; font-weight: bold; text-align: center; float: left">styled</p>', '<p style="color: red; background-color: blue; font-weight: bold; text-align: center;">styled</p>'),
	('<a href="javascript:alert(1)">js</a>', "<p><a>js</a></p>"),
	('<a href="https://example.com" target="_self" rel="opener" title="t">a</a>', f'<p>{_link("https://example.com", "a")}</p>'),
	('<a href="/x" target="_self" rel="opener">a</a>', '<p><a href="/x">a</a></p>'),
	('<a href="/x" target="_blank" rel="nofollow noopener noreferrer">a</a>', '<p><a href="/x" target="_blank" rel="nofollow noopener noreferrer">a</a></p>'),
	('<span style="color: red; float: left">s</span> <b style="font-weight: bold">b</b>', '<p><span style="color: red;">s</span> <b style="font-weight: bold;">b</b></p>'),
	('<table><tbody><tr><td style="text-align: center; width: 9px">d</td></tr></tbody></table>', '<table><tbody><tr><td style="text-align: center;">d</td></tr></tbody></table>'),
], ids=["kept elements", "table", "script", "div", "style", "iframe", "img", "event attribute", "paragraph attributes", "span attributes", "span other toggle", "style properties", "javascript link", "link attributes", "own link's other attributes", "own link written to open a new tab", "style on inline elements", "style in tables"])
def test_html_is_cleaned(body, html):
	assert_same_html(_rendered(body), html)


TABLE = "<table><thead><tr><th>h</th></tr></thead><tbody><tr><td>d</td></tr></tbody></table>"
RUBY = "<ruby>漢<rp>(</rp><rt>kan</rt><rp>)</rp></ruby>"
KEPT_ELEMENTS = {
	# element: (written, rendered)
	"a": ('x <a href="/x">t</a> y', '<p>x <a href="/x">t</a> y</p>'),
	"b": ("x <b>t</b> y", "<p>x <b>t</b> y</p>"),
	"blockquote": ("<blockquote>t</blockquote>", "<blockquote>t</blockquote>"),
	"br": ("x<br>y", "<p>x<br>y</p>"),
	"code": ("x <code>t</code> y", "<p>x <code>t</code> y</p>"),
	"del": ("x <del>t</del> y", "<p>x <del>t</del> y</p>"),
	"em": ("x <em>t</em> y", "<p>x <em>t</em> y</p>"),
	**{f"h{n}": (f"<h{n}>t</h{n}>", f"<h{n}>t</h{n}>") for n in range(1, 7)},
	"hr": ("<hr>", "<hr>"),
	"i": ("x <i>t</i> y", "<p>x <i>t</i> y</p>"),
	"li": ("<ul><li>t</li></ul>", "<ul><li>t</li></ul>"),
	"ol": ("<ol><li>t</li></ol>", "<ol><li>t</li></ol>"),
	"p": ("<p>t</p>", "<p>t</p>"),
	"pre": ("<pre>t</pre>", "<pre>t</pre>"),
	"rp": (RUBY, f"<p>{RUBY}</p>"),
	"rt": (RUBY, f"<p>{RUBY}</p>"),
	"ruby": (RUBY, f"<p>{RUBY}</p>"),
	"spoiler": ("x <spoiler>t</spoiler> y", "<p>x <spoiler>t</spoiler> y</p>"),
	"span": ("x <span>t</span> y", "<p>x <span>t</span> y</p>"),
	"strong": ("x <strong>t</strong> y", "<p>x <strong>t</strong> y</p>"),
	"sub": ("x <sub>t</sub> y", "<p>x <sub>t</sub> y</p>"),
	"sup": ("x <sup>t</sup> y", "<p>x <sup>t</sup> y</p>"),
	**{part: (TABLE, TABLE) for part in ("table", "thead", "tbody", "tr", "th", "td")},
	"ul": ("<ul><li>t</li></ul>", "<ul><li>t</li></ul>"),
}


@pytest.mark.parametrize("element", KEPT_ELEMENTS)
def test_each_kept_element_is_kept(element):
	written, rendered = KEPT_ELEMENTS[element]

	assert_same_html(_rendered(written), rendered)


DROPPED_ELEMENTS = {
	# element: (written, rendered)
	**{e: (f"x <{e}>t</{e}> y", "<p>x t y</p>") for e in ("u", "s", "strike", "ins", "mark", "small", "kbd", "abbr", "cite", "q")},
	"dl": ("<dl><dt>a</dt><dd>b</dd></dl>", "a\nb"),
	"details": ("<details><summary>a</summary>b</details>", "ab"),
	"caption": ("<table><caption>c</caption><tbody><tr><td>d</td></tr></tbody></table>", "c<table><tbody><tr><td>d</td></tr></tbody></table>"),
	"tfoot": ("<table><tbody><tr><td>d</td></tr></tbody><tfoot><tr><td>f</td></tr></tfoot></table>", "<table><tbody><tr><td>d</td></tr></tbody><tbody><tr><td>f</td></tr></tbody></table>"),
	"colgroup": ('<table><colgroup><col span="1"></colgroup><tbody><tr><td>d</td></tr></tbody></table>', "<table><tbody><tr><td>d</td></tr></tbody></table>"),
	"img": ('x <img src="https://example.com/y.png" alt="a"> y', "<p>x  y</p>"),
	"video": ('x <video src="https://example.com/v.mp4">t</video> y', "<p>x t y</p>"),
	"audio": ('x <audio src="https://example.com/a.mp3">t</audio> y', "<p>x t y</p>"),
	"form": ('<form action="https://example.com"><input name="n" value="v">t</form>', "t"),
	"input": ('x <input name="n" value="v"> y', "<p>x  y</p>"),
	"textarea": ("<textarea><b>x</b></textarea>", "&lt;b&gt;x&lt;/b&gt;"),
	"select": ("<select><option>o</option></select>", "<p>o</p>"),
	"noscript": ("<noscript><b>x</b></noscript>", "<p><b>x</b></p>"),
	"svg": ('<svg><a href="https://example.com">x</a></svg>', f'<p>{_link("https://example.com", "x")}</p>'),
	"math": ("<math><mi>x</mi></math>", "<p>x</p>"),
	"template": ("<template><b>x</b></template>", "<p><b>x</b></p>"),
	"title": ("<title>x</title>", "x"),
}


@pytest.mark.parametrize("element", DROPPED_ELEMENTS)
def test_each_other_element_is_dropped(element):
	written, rendered = DROPPED_ELEMENTS[element]

	assert_same_html(_rendered(written), rendered)


@pytest.mark.parametrize("address, html", [
	("foo", f'<p>{_link("foo", "x")}</p>'),
	("#f", f'<p>{_link("#f", "x")}</p>'),
	("?q=1", f'<p>{_link("?q=1", "x")}</p>'),
	("HTTPS://example.com/x", f'<p>{_link("HTTPS://example.com/x", "x")}</p>'),
	("mailto:a@b.com", "<p><a>x</a></p>"),
	("ftp://example.com/x", "<p><a>x</a></p>"),
	("data:text/html,x", "<p><a>x</a></p>"),
], ids=["relative", "fragment", "query", "scheme in capitals", "mail", "other scheme", "data"])
def test_a_link_keeps_its_address_unless_it_has_another_scheme(address, html):
	assert_same_html(_rendered(f'<a href="{address}">x</a>'), html)


@pytest.mark.parametrize("body, html", [
	("[link](https://example.com/x)", f'<p>{_link("https://example.com/x", "link")}</p>'),
	("[local](/leaderboard)", '<p><a href="/leaderboard">local</a></p>'),
	("<https://example.com/auto>", f'<p>{_link("https://example.com/auto")}</p>'),
	("see https://example.com/bare.", f'<p>see {_link("https://example.com/bare")}.</p>'),
	("example.com", f'<p>{_link("http://example.com", "example.com")}</p>'),
	("www.example.com/p", f'<p>{_link("http://www.example.com/p", "www.example.com/p")}</p>'),
	("notes.txt", "<p>notes.txt</p>"),
	("mailto:a@b.com a@b.com", "<p>mailto:a@b.com a@b.com</p>"),
	("ftp://example.com/x", f'<p>ftp://{_link("http://example.com/x", "example.com/x")}</p>'),
	("```\nhttps://example.com\n```", "<pre><code>https://example.com\n</code></pre>"),
	("[https://evil.example](https://good.example)", f'<p>{_link("https://good.example")}</p>'),
	("[x](https://example.com/a~b~c)", f'<p>{_link("https://example.com/a~b~c", "x")}</p>'),
	("https://example.com/?utm_source=x&a=1 https://example.com/?a=1&utm_medium=y", f'<p>{_link("https://example.com/?a=1")} {_link("https://example.com/?a=1")}</p>'),
], ids=["markdown link", "site path", "autolink", "bare address", "bare host", "www host", "unknown top-level domain", "mail", "other scheme", "in a code block", "address as text", "tildes in an address", "tracking parameters"])
def test_links(body, html):
	assert_same_html(_rendered(body), html)


def test_links_to_the_site_itself_stay_in_the_tab():
	address = config.site_url() + "/leaderboard"

	assert_same_html(_rendered(f"[here]({address})"), f'<p><a href="{address}">here</a></p>')


TOP_LEVEL_DOMAINS = ("ac", "ad", "ae", "aero", "af", "ag", "ai", "al", "am", "an", "ao", "aq", "ar", "arpa", "as", "asia", "at", "au", "aw", "ax", "az", "ba", "bb", "bd", "be", "bf", "bg", "bh", "bi", "biz", "bj", "bm", "bn", "bo", "br", "bs", "bt", "bv", "bw", "by", "bz", "ca", "cafe", "cat", "cc", "cd", "cf", "cg", "ch", "ci", "ck", "cl", "club", "cm", "cn", "co", "com", "coop", "cr", "cu", "cv", "cx", "cy", "cz", "de", "dj", "dk", "dm", "do", "dz", "ec", "edu", "ee", "eg", "er", "es", "et", "eu", "fi", "fj", "fk", "fm", "fo", "fr", "ga", "gb", "gd", "ge", "gf", "gg", "gh", "gi", "gl", "gm", "gn", "gov", "gp", "gq", "gr", "gs", "gt", "gu", "gw", "gy", "hk", "hm", "hn", "hr", "ht", "hu", "id", "ie", "il", "im", "in", "info", "int", "io", "iq", "ir", "is", "it", "je", "jm", "jo", "jobs", "jp", "ke", "kg", "kh", "ki", "km", "kn", "kp", "kr", "kw", "ky", "kz", "la", "lb", "lc", "li", "lk", "lr", "ls", "lt", "lu", "lv", "ly", "ma", "mc", "md", "me", "mg", "mh", "mil", "mk", "ml", "mm", "mn", "mo", "mobi", "moe", "mp", "mq", "mr", "ms", "mt", "mu", "museum", "mv", "mw", "mx", "my", "mz", "na", "name", "nc", "ne", "net", "nf", "ng", "ni", "nl", "no", "np", "nr", "nu", "nz", "om", "org", "pa", "pe", "pf", "pg", "ph", "pk", "pl", "pm", "pn", "post", "pr", "pro", "ps", "pt", "pw", "py", "qa", "re", "ro", "rs", "ru", "rw", "sa", "sb", "sc", "sd", "se", "sg", "sh", "si", "sj", "sk", "sl", "sm", "sn", "so", "social", "sr", "ss", "st", "su", "sv", "sx", "sy", "sz", "tc", "td", "tel", "tf", "tg", "th", "tj", "tk", "tl", "tm", "tn", "to", "tp", "tr", "travel", "tt", "tv", "tw", "tz", "ua", "ug", "uk", "us", "uy", "uz", "va", "vc", "ve", "vg", "vi", "vn", "vu", "wf", "win", "ws", "xn", "xxx", "xyz", "ye", "yt", "yu", "za", "zm", "zw")


@pytest.mark.parametrize("tld", TOP_LEVEL_DOMAINS)
def test_addresses_under_each_top_level_domain_become_links(tld):
	host = f"a.{tld}"

	assert_same_html(_rendered(f"{host} https://{host}/x"), f'<p>{_link(f"http://{host}", host)} {_link(f"https://{host}/x")}</p>')


@pytest.mark.parametrize("host", ["localhost", "192.168.0.1", "a.dev", "a.app", "a.online", "a.zip"])
def test_addresses_under_other_names_stay_text(host):
	assert host.rsplit(".", 1)[-1] not in TOP_LEVEL_DOMAINS

	assert_same_html(_rendered(f"{host} https://{host}/x"), f"<p>{host} https://{host}/x</p>")


REWRITES = [
	# (written, becomes), replaced in this order
	("://reddit.com", "://old.reddit.com"),
	("://new.reddit.com", "://old.reddit.com"),
	("://www.reddit.com", "://old.reddit.com"),
	("://redd.it", "://old.reddit.com"),
	("://libredd.it", "://old.reddit.com"),
	("://teddit.net", "://old.reddit.com"),
	("nitter.net", "twitter.com"),
	("old.reddit.com/gallery", "reddit.com/gallery"),
	("https://youtu.be/", "https://youtube.com/watch?v="),
	("https://music.youtube.com/watch?v=", "https://youtube.com/watch?v="),
	("https://streamable.com/", "https://streamable.com/e/"),
	("https://youtube.com/shorts/", "https://youtube.com/watch?v="),
	("https://mobile.twitter", "https://twitter"),
	("https://m.facebook", "https://facebook"),
	("m.wikipedia.org", "wikipedia.org"),
	("https://m.youtube", "https://youtube"),
	("https://www.youtube", "https://youtube"),
	("https://www.twitter", "https://twitter"),
	("https://www.instagram", "https://instagram"),
	("https://www.tiktok", "https://tiktok"),
]
REWRITE_EXAMPLES = [
	("https://reddit.com/r/x", "https://old.reddit.com/r/x"),
	("https://www.reddit.com/r/x", "https://old.reddit.com/r/x"),
	("https://new.reddit.com/r/x", "https://old.reddit.com/r/x"),
	("https://redd.it/x", "https://old.reddit.com/x"),
	("https://libredd.it/r/x", "https://old.reddit.com/r/x"),
	("https://teddit.net/r/x", "https://old.reddit.com/r/x"),
	("https://www.reddit.com/gallery/x", "https://reddit.com/gallery/x"),
	("https://nitter.net/x", "https://twitter.com/x"),
	("https://mobile.twitter.com/x", "https://twitter.com/x"),
	("https://www.twitter.com/x", "https://twitter.com/x"),
	("https://youtu.be/abcde", "https://youtube.com/watch?v=abcde"),
	("https://music.youtube.com/watch?v=abcde", "https://youtube.com/watch?v=abcde"),
	("https://youtube.com/shorts/abcde", "https://youtube.com/watch?v=abcde"),
	("https://m.youtube.com/watch?v=abcde", "https://youtube.com/watch?v=abcde"),
	("https://www.youtube.com/watch?v=abcde", "https://youtube.com/watch?v=abcde"),
	("https://youtu.be/abcde?t=5", "https://youtube.com/watch?v=abcde&t=5"),
	("https://streamable.com/abc", "https://streamable.com/e/abc"),
	("https://m.facebook.com/x", "https://facebook.com/x"),
	("https://en.m.wikipedia.org/wiki/X", "https://en.wikipedia.org/wiki/X"),
	("https://www.instagram.com/x", "https://instagram.com/x"),
	("https://www.tiktok.com/x", "https://tiktok.com/x"),
	("https://www.youtube.com/shorts/abcde", "https://youtube.com/shorts/abcde"),
	("http://reddit.com/r/x", "http://old.reddit.com/r/x"),
	("https://xnitter.net/x", "https://xtwitter.com/x"),
	("http://www.youtube.com/watch?v=abcde", "http://www.youtube.com/watch?v=abcde"),
	("http://m.facebook.com/x", "http://m.facebook.com/x"),
]


def test_the_rewrite_examples_follow_the_table():
	'''Each example's address is rewritten by applying REWRITES in order (then the YouTube start time), and every replacement applies in some example.'''
	applied = set()

	def rewrite(address):
		for written, becomes in REWRITES:
			if written in address:
				applied.add(written)
				address = address.replace(written, becomes)
		return address.replace("?t=", "&t=") if address.startswith("https://youtube.com/watch?v=") else address

	assert [rewrite(address) for address, _ in REWRITE_EXAMPLES] == [rewritten for _, rewritten in REWRITE_EXAMPLES]
	assert [written for written, _ in REWRITES if written not in applied] == []


@pytest.mark.parametrize("address, rewritten", REWRITE_EXAMPLES)
def test_some_sites_addresses_are_rewritten(address, rewritten):
	assert_same_html(_rendered(address), f'<p>{_link(rewritten)}</p>')


def test_a_link_showing_its_address_shows_it_rewritten():
	assert_same_html(_rendered("I read nitter.net"), f'<p>I read {_link("http://twitter.com", "twitter.com")}</p>')


@pytest.mark.parametrize("body, html", [
	("`nitter.net and https://youtu.be/abcde?utm_source=x&a=1 &amp;`", "<p><code>nitter.net and https://youtu.be/abcde?utm_source=x&amp;a=1 &amp;amp;</code></p>"),
	("my_utm_a=b&c", "<p>my_utm_a=b&amp;c</p>"),
	("https://example.com/x?t=1 https://youtu.be/abcde?t=5", f'<p>{_link("https://example.com/x?t=1")} {_link("https://youtube.com/watch?v=abcde&t=5")}</p>'),
	("[a & b](https://example.com/?x=1&y=2)", f'<p>{_link("https://example.com/?x=1&amp;y=2", "a &amp; b")}</p>'),
], ids=["in code", "in prose", "other addresses' times", "ampersands"])
def test_addresses_are_rewritten_and_cleaned_only_where_they_are_addresses(body, html):
	assert_same_html(_rendered(body), html)


@pytest.mark.parametrize("body, html", [
	("~struck~ and ~~double~~", "<p><del>struck</del> and <del>double</del></p>"),
	("~one~~", "<p><del>one</del>~</p>"),
	("||hidden||", "<p><spoiler>hidden</spoiler></p>"),
	("/r/motte and u/some-one", '<p><a href="https://old.reddit.com/r/motte" target="_blank" rel="nofollow noopener noreferrer">/r/motte</a> and <a href="https://old.reddit.com/u/some-one" target="_blank" rel="nofollow noopener noreferrer">/u/some-one</a></p>'),
	("/r/ab", "<p>/r/ab</p>"),
	("`/r/motte`", "<p><code>/r/motte</code></p>"),
	("/h/hole", '<p><a href="/h/hole">/h/hole</a></p>'),
	("zero​width‎mark‏﻿\U0001242a!", "<p>zerowidthmark!</p>"),
], ids=["strikethrough", "tildes pair by count", "spoiler", "reddit names", "reddit name too short", "reddit name in code", "hole", "invisible characters"])
def test_text_conventions(body, html):
	assert_same_html(_rendered(body), html)


@pytest.mark.parametrize("body, html", [
	("`~/.bashrc and ~/x`", "<p><code>~/.bashrc and ~/x</code></p>"),
	("```\n~a~ ||b||\n```", "<pre><code>~a~ ||b||\n</code></pre>"),
	("`||not hidden||` but ||hidden||", "<p><code>||not hidden||</code> but <spoiler>hidden</spoiler></p>"),
	("`x /r/motte /h/hole @nobody`", "<p><code>x /r/motte /h/hole @nobody</code></p>"),
	("https://example.com/~a~", f'<p>{_link("https://example.com/~a~")}</p>'),
	("~a **b** c~", "<p>~a <strong>b</strong> c~</p>"),
	("/r/" + "a" * 26, "<p>/r/" + "a" * 26 + "</p>"),
], ids=["code span", "code block", "code beside a spoiler", "names in code", "tildes in a bare address", "across markup", "reddit name too long"])
def test_code_shows_its_text_as_written(body, html):
	assert_same_html(_rendered(body), html)


def test_other_texts_render_the_same_way():
	'''Posts, bios and friends lists take the rules above as comments do.'''
	author = factories.user()
	body = "**bold** ~struck~ https://example.com"
	expected = f'<p><strong>bold</strong> <del>struck</del> {_link("https://example.com")}</p>'

	assert_status(as_user(author).post("/submit", {"title": factories.unique("title"), "body": body}, headers=XHR), 200)
	assert_html(as_user(author).post("/settings/profile", {"bio": body}), 200)

	[post] = db.rows("submissions", author_id=author["id"])
	assert_same_html(post["body_html"], expected)
	assert_same_html(db.row("users", id=author["id"])["bio_html"], expected)


@pytest.mark.parametrize("banned, address", [
	("example.com", "https://example.com/x"),
	("example.com", "https://sub.example.com/x"),
	("example.com/bad", "https://example.com/bad"),
], ids=["host", "parent domain", "host and path"])
def test_linking_a_banned_domain_is_refused(banned, address):
	db.insert("banneddomains", domain=banned, reason="spam")
	author, post = factories.user(), factories.post(factories.user())

	with db_diff() as d:
		r = _comment(author, post, f"see {address}")

	assert_status(r, 403)
	d.assert_exactly()


def test_a_banned_hosts_other_paths_are_allowed():
	db.insert("banneddomains", domain="example.com/bad", reason="spam")

	assert_same_html(_rendered("https://example.com/fine"), f'<p>{_link("https://example.com/fine")}</p>')
