'''
Reporting a post or a comment: POST /report/post/<post id> and POST /report/comment/<comment id>, with the form field "reason" (optional). The answer is a JSON "message".

A report is stored with its reporter and its reason, and opens the item's reports ("state_report" becomes REPORTED, also when they were resolved before) unless an admin chose to ignore its reports (IGNORED), which a new report doesn't change. Every report is stored, repeated ones by the same user included.

The reason is stored rendered, in this order: surrounding whitespace trimmed, cut to its first 100 characters, invisible formatting characters removed (zero-width spaces, left-to-right and right-to-left marks, byte-order marks), runs of whitespace made one space, HTML-escaped, and text between tildes (~like this~) struck through as <del>. Where the rendering of those 100 characters would be longer than 350 characters, as many characters are kept as fit rendered into 350. No reason stores "".

Anything the reporter can open can be reported, also what shows them only a placeholder: a removed, held, deleted or shadowbanned user's item, or one by a user they block. API clients report as their user.

An admin of level 2 or higher (in their own browser session; API clients act as level 0) reporting a post with a reason starting with "!" sets the post's flair instead: the flair is the rest of the rendered reason ("" for a lone "!"), keeping only as many characters as fit rendered into a 254-character flair, the mod log records a "flair_post" action noting the flair in double quotes, and no report is stored. On comments, and for everyone else, such a reason is an ordinary one.

Refused, changing nothing: anonymous users (401 to scripts); an unknown id, or one that isn't a whole number (404); an item the reporter can't open (404): a draft, or a comment on one, unless they are its author or an admin of level 2 or higher; a private message unless they take part in its conversation (or are such an admin); one of the site's notices unless it notified them (or they are such an admin).
'''
import pytest

from files.tests.spec.harness import *

KINDS = ["post", "comment"]
_TABLES = {"post": ("submissions", "flags", "post_id"), "comment": ("comments", "commentflags", "comment_id")}


def _item(kind, author=None, **overrides):
	author = author or factories.user()
	if kind == "post":
		return factories.post(author, **overrides)
	return factories.comment(author, factories.post(factories.user()), **overrides)


def _report(client, kind, item, reason=None, **kwargs):
	data = {} if reason is None else {"reason": reason}
	return client.post(f"/report/{kind}/{item['id']}", data, headers=XHR, **kwargs)


def _stored(kind, reporter, item, reason):
	_, flags, key = _TABLES[kind]
	return {flags: [{key: item["id"], "user_id": reporter["id"], "reason": reason}]}


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("before", ["UNREPORTED", "RESOLVED"])
def test_a_report_is_stored_and_opens_the_items_reports(kind, before):
	item = _item(kind, state_report=before)
	reporter = factories.user()
	reason = factories.unique()

	with db_diff() as d:
		r = _report(as_user(reporter), kind, item, reason)

	assert_json_message(r)
	d.assert_exactly(inserted=_stored(kind, reporter, item, reason), updated={_TABLES[kind][0]: {item["id"]: {"state_report": "REPORTED"}}})


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("state", ["REPORTED", "IGNORED"])
def test_a_report_of_an_item_whose_reports_are_open_or_ignored_is_only_stored(kind, state):
	item = _item(kind, state_report=state)
	reporter = factories.user()
	factories.report(factories.user(), item)

	with db_diff() as d:
		r = _report(as_user(reporter), kind, item, "again")

	assert_json_message(r)
	d.assert_exactly(inserted=_stored(kind, reporter, item, "again"))


@pytest.mark.parametrize("kind", KINDS)
def test_repeated_reports_by_one_user_are_each_stored(kind):
	item = _item(kind, state_report="REPORTED")
	reporter = factories.user()
	factories.report(reporter, item, "first")

	with db_diff() as d:
		_report(as_user(reporter), kind, item, "second")

	d.assert_exactly(inserted=_stored(kind, reporter, item, "second"))


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("sent, stored", [
	(None, ""),
	("", ""),
	("  spaced \t  out\n", "spaced out"),
	("in​visible‎", "invisible"),
	("<b>bold</b> & \"quoted\" 'too'", "&lt;b&gt;bold&lt;/b&gt; &amp; &quot;quoted&quot; &#x27;too&#x27;"),
	("a ~struck~ word", "a <del>struck</del> word"),
	("x" * 99 + "yz", "x" * 99 + "y"),
	("   " + "x" * 100 + "   ", "x" * 100),
	("\u200b" * 100 + "x", ""),
	("<" * 100, "&lt;" * 87),
	("x" * 40 + "\"" * 60, "x" * 40 + "&quot;" * 51),
	("&" * 69 + "x" * 6, "&amp;" * 69 + "x" * 5),
], ids=["missing", "empty", "whitespace", "invisible", "escaped", "struck", "cut", "trimmed-then-cut", "cut-then-made-visible", "escapes-fit", "escapes-fit-after-text", "escapes-fit-exactly"])
def test_the_reason_is_stored_rendered(kind, sent, stored):
	item = _item(kind)
	reporter = factories.user()

	with db_diff() as d:
		_report(as_user(reporter), kind, item, sent)

	d.assert_exactly(inserted=_stored(kind, reporter, item, stored), updated={_TABLES[kind][0]: {item["id"]: {"state_report": "REPORTED"}}})


_PLACEHOLDERS = {
	"removed": lambda: {"state_mod": "REMOVED"},
	"held": lambda: {"state_mod": "FILTERED"},
	"deleted": lambda: {"state_user_deleted_utc": "2020-01-01T00:00:00Z"},
}


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("hidden", [*_PLACEHOLDERS, "shadowbanned author", "blocked author"])
def test_items_shown_as_placeholders_can_be_reported(kind, hidden):
	reporter = factories.user()
	author = factories.user(shadowbanned="somemod") if hidden == "shadowbanned author" else factories.user()
	if hidden == "blocked author":
		db.insert("userblocks", user_id=reporter["id"], target_id=author["id"])
	item = _item(kind, author, **(_PLACEHOLDERS[hidden]() if hidden in _PLACEHOLDERS else {}))

	with db_diff() as d:
		r = _report(as_user(reporter), kind, item, "seen")

	assert_json_message(r)
	d.assert_exactly(inserted=_stored(kind, reporter, item, "seen"), updated={_TABLES[kind][0]: {item["id"]: {"state_report": "REPORTED"}}})


@pytest.mark.parametrize("kind", KINDS)
def test_api_clients_report_as_their_user(kind):
	item = _item(kind)
	reporter = factories.user()
	client = as_api(factories.api_token(reporter))

	with db_diff() as d:
		r = client.post(f"/report/{kind}/{item['id']}", {"reason": "bot"})

	assert_json_message(r)
	d.assert_exactly(inserted=_stored(kind, reporter, item, "bot"), updated={_TABLES[kind][0]: {item["id"]: {"state_report": "REPORTED"}}})


@pytest.mark.parametrize("kind", KINDS)
def test_anonymous_reports_are_unauthorized(kind):
	item = _item(kind)

	with db_diff() as d:
		r = _report(anon(), kind, item, "anon")

	assert_api_unauthorized(r)
	d.assert_exactly()


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("bad", ["unknown", "garbled", "huge"])
def test_ids_that_are_no_items_are_not_found(kind, bad):
	ids = {"unknown": lambda: db.execute(f"SELECT nextval('{_TABLES[kind][0]}_id_seq')"), "garbled": lambda: "abc", "huge": lambda: str(2**31)}
	client = as_user(factories.user())

	with db_diff() as d:
		r = _report(client, kind, {"id": ids[bad]()}, "nothing")

	assert_status(r, 404)
	d.assert_exactly()


# Flair

@pytest.mark.parametrize("sent, flair", [
	("!Megathread", "Megathread"),
	("!", ""),
	("!<i>x</i> & ~y~", "&lt;i&gt;x&lt;/i&gt; &amp; <del>y</del>"),
	("!" + "&" * 99, "&amp;" * 50),
], ids=["plain", "empty", "rendered", "escapes-fit"])
def test_admins_set_a_posts_flair_by_reporting_it_with_a_bang(sent, flair):
	post = _item("post")
	admin = factories.admin(2)

	with db_diff() as d:
		r = _report(as_user(admin), "post", post, sent)

	assert_json_message(r)
	d.assert_exactly(
		updated={"submissions": {post["id"]: {"flair": flair}}},
		inserted={"modactions": [{"kind": "flair_post", "user_id": admin["id"], "target_submission_id": post["id"], "target_comment_id": None, "target_user_id": None, "_note": f'"{flair}"'}]},
	)


@pytest.mark.parametrize("who", ["user", "helper", "admin's API client"])
def test_a_bang_from_others_is_an_ordinary_reason(who):
	post = _item("post")
	reporter = factories.admin(1) if who == "helper" else factories.admin(2) if who == "admin's API client" else factories.user()
	client = as_api(factories.api_token(reporter)) if who == "admin's API client" else as_user(reporter)

	with db_diff() as d:
		client.post(f"/report/post/{post['id']}", {"reason": "!Megathread"}, headers=XHR)

	d.assert_exactly(inserted=_stored("post", reporter, post, "!Megathread"), updated={"submissions": {post["id"]: {"state_report": "REPORTED"}}})


def test_a_bang_on_a_comment_is_an_ordinary_reason_even_for_admins():
	comment = _item("comment")
	admin = factories.admin(3)

	with db_diff() as d:
		_report(as_user(admin), "comment", comment, "!Megathread")

	d.assert_exactly(inserted=_stored("comment", admin, comment, "!Megathread"), updated={"comments": {comment["id"]: {"state_report": "REPORTED"}}})


# What can't be opened

def _draft_comment(author):
	return factories.comment(author, factories.post(author, private=True))


@pytest.mark.parametrize("kind", KINDS)
def test_others_drafts_are_not_found(kind):
	author = factories.user()
	item = factories.post(author, private=True) if kind == "post" else _draft_comment(author)
	client = as_user(factories.user())

	with db_diff() as d:
		r = _report(client, kind, item, "peek")

	assert_status(r, 404)
	d.assert_exactly()


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("who", ["author", "admin"])
def test_drafts_can_be_reported_by_those_who_see_them(kind, who):
	author = factories.user()
	item = factories.post(author, private=True) if kind == "post" else _draft_comment(author)
	reporter = author if who == "author" else factories.admin(2)

	with db_diff() as d:
		r = _report(as_user(reporter), kind, item, "mine")

	assert_json_message(r)
	d.assert_exactly(inserted=_stored(kind, reporter, item, "mine"), updated={_TABLES[kind][0]: {item["id"]: {"state_report": "REPORTED"}}})


@pytest.mark.parametrize("who", ["user", "helper"])
def test_others_private_messages_are_not_found(who):
	message = factories.message(factories.user(), factories.user())
	client = as_user(factories.admin(1) if who == "helper" else factories.user())

	with db_diff() as d:
		r = _report(client, "comment", message, "peek")

	assert_status(r, 404)
	d.assert_exactly()


@pytest.mark.parametrize("who", ["sender", "recipient", "admin"])
def test_private_messages_can_be_reported_by_those_who_open_them(who):
	sender, recipient = factories.user(), factories.user()
	message = factories.message(sender, recipient)
	reporter = {"sender": sender, "recipient": recipient, "admin": factories.admin(2)}[who]

	with db_diff() as d:
		r = _report(as_user(reporter), "comment", message, "rude")

	assert_json_message(r)
	d.assert_exactly(inserted=_stored("comment", reporter, message, "rude"), updated={"comments": {message["id"]: {"state_report": "REPORTED"}}})


@pytest.mark.parametrize("notified", [True, False])
def test_notices_can_be_reported_only_by_those_they_notified(notified):
	user = factories.user()
	notice = factories.message(db.row("users", id=seed.SYSTEM_ID), None)
	if notified:
		factories.notification(user, notice)

	with db_diff() as d:
		r = _report(as_user(user), "comment", notice, "spam")

	if notified:
		assert_json_message(r)
		d.assert_exactly(inserted=_stored("comment", user, notice, "spam"), updated={"comments": {notice["id"]: {"state_report": "REPORTED"}}})
	else:
		assert_status(r, 404)
		d.assert_exactly()
