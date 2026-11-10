'''
The mod log, open to everyone: GET /log (also /modlog) lists entries newest first, 25 to a page ("page", see listings/test_parameters); GET /log/<id> shows one entry, and an id that isn't written as a plain whole number (ASCII digits, no leading zero) is 404, as is one that names no entry. An entry shows the admin who made it and what it was about.

The list takes two filters: "admin", a username, for that account's entries only (an unknown name is 404), and "kind", for entries of that kind only. A kind the site doesn't know, or one the viewer may not see, is ignored.

Some kinds of entry are shown only to admins (level 2+): shadowbanning and unshadowbanning, setting a post's flair, editing a post, linking alt accounts, and setting a user's filter mode. To anyone else (visitors, users below level 2, and API clients whatever their account's level) such an entry doesn't exist: the list leaves it out and its page is 404.

The kinds the site knows are MOD_LOG_KINDS below, which says for each what its entries are about (a user, a post, a comment, or the site as a whole, which is the target column the site fills; the spec of each action pins what it writes) and whether it's shown only to admins. An entry shows what it is about. The kind filter takes exactly these. An entry of a change to a whole-number site setting (kind "set_<value>_for_<setting>", cut to 32 characters, see test_dashboard) names the setting in full and the value; those kinds can't be filtered on. An entry of a kind the site doesn't know is still listed, with the admin who made it.

An entry names the post or comment it's about (a post by its title, both with a link to them), unless the viewer couldn't open it: a draft (or a comment on one), seen only by its author and admins from level 2; a private message, seen only by those taking part in its conversation and admins from level 2 (a shadowbanned user's too); or a post or comment by a shadowbanned user, seen only by that user (admins see it only on that user's profile). For anyone else the entry stays, saying only that it was a post or a comment, with no title or link. A ban's note, which links the post or comment the ban was for, follows the same rule.
'''
import re
from typing import NamedTuple

import pytest

from files.tests.spec.harness import *


class Kind(NamedTuple):
	target: str | None
	'''What an entry of the kind is about, in the column the site fills: "user" (target_user_id), "post" (target_submission_id), "comment" (target_comment_id), or None for the site as a whole.'''
	admin_only: bool = False


USER, POST, COMMENT, SITE = Kind("user"), Kind("post"), Kind("comment"), Kind(None)

MOD_LOG_KINDS = {
	"approve_app": USER,
	"approve_comment": COMMENT,
	"approve_post": POST,
	"ban_domain": SITE,
	"ban_user": USER,
	"check": USER,
	"disabled_Bots": SITE,
	"disabled_FilterNewPosts": SITE,
	"disabled_Read-only_mode": SITE,
	"disabled_Signups": SITE,
	"distinguish_comment": COMMENT,
	"distinguish_post": POST,
	"dump_cache": SITE,
	"edit_post": Kind("post", admin_only=True),
	"enabled_Bots": SITE,
	"enabled_FilterNewPosts": SITE,
	"enabled_Read-only_mode": SITE,
	"enabled_Signups": SITE,
	"filter_auto": Kind("user", admin_only=True),
	"filter_off": Kind("user", admin_only=True),
	"filter_on": Kind("user", admin_only=True),
	"flair_post": Kind("post", admin_only=True),
	"link_accounts": Kind("user", admin_only=True),
	"make_admin": USER,
	"nuke_user": USER,
	"pin_comment": COMMENT,
	"pin_post": POST,
	"reject_app": USER,
	"remove_admin": USER,
	"remove_comment": COMMENT,
	"remove_post": POST,
	"revert": USER,
	"revoke_app": USER,
	"set_flair_locked": USER,
	"set_flair_notlocked": USER,
	"set_nsfw": POST,
	"shadowban": Kind("user", admin_only=True),
	"unban_domain": SITE,
	"unban_user": USER,
	"uncheck": USER,
	"undistinguish_comment": COMMENT,
	"undistinguish_post": POST,
	"unnuke_user": USER,
	"unpin_comment": COMMENT,
	"unpin_post": POST,
	"unset_nsfw": POST,
	"unshadowban": Kind("user", admin_only=True),
}
'''Every kind of entry the site knows, with what an entry of it is about and whether it's shown only to admins (level 2+).'''

ADMIN_ONLY_KINDS = [name for name, kind in MOD_LOG_KINDS.items() if kind.admin_only]
NON_ADMINS = {
	"visitor": anon,
	"level 1": lambda: as_user(factories.admin(1)),
	"admin's API client": lambda: as_api(factories.api_token(factories.admin(3))),
}


def _entry(kind):
	'''An entry of `kind` against a fresh user, whose username is the returned sentinel.'''
	target = factories.user()
	entry = db.insert("modactions", user_id=factories.admin(2)["id"], kind=kind, target_user_id=target["id"])
	return entry, target["username"]


@pytest.mark.parametrize("kind", ADMIN_ONLY_KINDS)
def test_admins_see_an_admin_only_entry(kind):
	entry, target = _entry(kind)

	r = as_user(factories.admin(2)).get(f"/log/{entry['id']}")

	assert_html(r, 200)
	assert_in_payload(r, target)


@pytest.mark.parametrize("kind", ADMIN_ONLY_KINDS)
def test_admins_find_admin_only_entries_in_the_list(kind):
	_, target = _entry(kind)

	r = as_user(factories.admin(2)).get("/log")

	assert_html(r, 200)
	assert_in_payload(r, target)


@pytest.mark.parametrize("viewer", NON_ADMINS)
@pytest.mark.parametrize("kind", ADMIN_ONLY_KINDS)
def test_the_list_leaves_out_admin_only_entries_for_others(kind, viewer):
	_, target = _entry(kind)

	r = NON_ADMINS[viewer]().get("/log")

	assert_html(r, 200)
	assert_not_in_payload(r, target)


@pytest.mark.parametrize("viewer", NON_ADMINS)
@pytest.mark.parametrize("kind", ADMIN_ONLY_KINDS)
def test_an_admin_only_entry_doesnt_exist_for_others(kind, viewer):
	entry, target = _entry(kind)

	r = NON_ADMINS[viewer]().get(f"/log/{entry['id']}")

	assert_status(r, 404)


@pytest.mark.parametrize("spelling", [lambda id: f"0_{id}", lambda id: f"%20{id}", lambda id: f"+{id}", lambda id: f"{id}.0", lambda id: f"0{id}", lambda id: "".join(chr(0xFF10 + int(d)) for d in str(id))], ids=["underscore", "leading space", "plus sign", "decimal", "leading zero", "fullwidth digits"])
def test_an_id_must_be_written_plainly(spelling):
	entry, _ = _entry("ban_user")

	r = anon().get(f"/log/{spelling(entry['id'])}")

	assert_status(r, 404)


@pytest.mark.parametrize("id", ["abc", "-1", str(2**31), lambda: db.execute("SELECT nextval('modactions_id_seq')")], ids=["garbled", "negative", "too large", "unknown"])
def test_ids_that_are_no_entry_are_not_found(id):
	assert_status(anon().get(f"/log/{id() if callable(id) else id}"), 404)


TARGET_VIEWERS = {
	"visitor": (lambda author: anon(), False),
	"user": (lambda author: as_user(factories.user()), False),
	"shadowbanned user": (lambda author: as_user(factories.user(shadowbanned="somemod")), False),
	"level 1": (lambda author: as_user(factories.admin(1)), False),
	"admin's API client": (lambda author: as_api(factories.api_token(factories.admin(3))), False),
	"author": (lambda author: as_user(author), True),
	"admin": (lambda author: as_user(factories.admin(2)), True),
}
'''Who opens a hidden draft (the second item); a shadowbanned author's items open only to the author.'''
HIDDEN_POSTS = {
	"draft": lambda: (factories.user(), {"private": True}),
	"shadowbanned author": lambda: (factories.user(shadowbanned="somemod"), {}),
}


def _sees(viewer, hidden) -> bool:
	return viewer == "author" if hidden == "shadowbanned author" else TARGET_VIEWERS[viewer][1]


def _post_entry(kind, author, **post_overrides):
	post = factories.post(author, **post_overrides)
	entry = db.insert("modactions", user_id=factories.admin(2)["id"], kind=kind, target_submission_id=post["id"])
	return entry, post


def _shows_post(r, entry, post) -> bool:
	text = element_text(r, f"action-{entry['id']}")
	assert text, "the entry is listed"
	shown = post["title"] in text, f"/post/{post['id']}" in r.text
	assert shown[0] == shown[1], f"title shown {shown[0]} but link shown {shown[1]}"
	return shown[0]


@pytest.mark.parametrize("viewer", TARGET_VIEWERS)
@pytest.mark.parametrize("hidden", HIDDEN_POSTS)
def test_a_post_the_viewer_couldnt_open_goes_unnamed(hidden, viewer):
	author, overrides = HIDDEN_POSTS[hidden]()
	entry, post = _post_entry("remove_post", author, **overrides)
	make_client, _ = TARGET_VIEWERS[viewer]

	r = make_client(author).get("/log")

	assert_html(r, 200)
	assert _shows_post(r, entry, post) == _sees(viewer, hidden)


def test_a_post_anyone_can_open_is_named():
	entry, post = _post_entry("remove_post", factories.user())

	r = anon().get(f"/log/{entry['id']}")

	assert_html(r, 200)
	assert _shows_post(r, entry, post)


@pytest.mark.parametrize("viewer", TARGET_VIEWERS)
@pytest.mark.parametrize("hidden", ["draft post", "shadowbanned author", None])
def test_a_comment_the_viewer_couldnt_open_goes_unlinked(hidden, viewer):
	author = factories.user(shadowbanned="somemod") if hidden == "shadowbanned author" else factories.user()
	comment = factories.comment(author, factories.post(author, private=hidden == "draft post"))
	entry = db.insert("modactions", user_id=factories.admin(2)["id"], kind="remove_comment", target_comment_id=comment["id"])
	make_client, _ = TARGET_VIEWERS[viewer]

	r = make_client(author).get("/log")

	assert_html(r, 200)
	assert element_text(r, f"action-{entry['id']}")
	assert (f"/comment/{comment['id']}" in r.text) == (hidden is None or _sees(viewer, hidden))


@pytest.mark.parametrize("viewer", ["visitor", "admin", "author"])
@pytest.mark.parametrize("target", ["post", "comment"])
def test_a_bans_note_links_what_it_was_for_only_if_the_viewer_could_open_it(target, viewer):
	author = factories.user(shadowbanned="somemod")
	post = factories.post(author)
	item = post if target == "post" else factories.comment(author, post)
	db.insert("modactions", user_id=factories.admin(2)["id"], kind="ban_user", target_user_id=author["id"], **({"target_submission_id": post["id"]} if target == "post" else {"target_comment_id": item["id"]}))
	make_client, _ = TARGET_VIEWERS[viewer]

	r = make_client(author).get("/log")

	assert_html(r, 200)
	link = f"/post/{post['id']}" if target == "post" else f"/comment/{item['id']}"
	assert (link in r.text) == _sees(viewer, "shadowbanned author")


@pytest.mark.parametrize("setting", ["FilterCommentsMinComments", "min_truescore_private_profile"])
def test_a_setting_change_names_the_setting_and_value(setting):
	entry = db.insert("modactions", user_id=factories.admin(3)["id"], kind=f"set_7316_for_{setting}"[:32])

	text = element_text(anon().get(f"/log/{entry['id']}"), f"action-{entry['id']}")

	assert setting.replace("_", " ") in text.replace("_", " ") and "7316" in text, text


def test_an_entry_of_an_unknown_kind_is_listed_with_its_admin():
	admin = factories.admin(2)
	entry = db.insert("modactions", user_id=admin["id"], kind=factories.unique("kind"))

	r = anon().get("/log")

	assert_html(r, 200)
	assert admin["username"] in element_text(r, f"action-{entry['id']}")


def _ids_listed(r) -> list[int]:
	return [int(m) for m in re.findall(r'id="action-(\d+)"', r.text)]


@pytest.mark.parametrize("path", ["/log", "/modlog"])
def test_the_list_shows_entries_newest_first_with_admin_and_target(path):
	admin = factories.admin(2)
	older, target = _entry("ban_user")
	newer = db.insert("modactions", user_id=admin["id"], kind="unban_user", target_user_id=factories.user()["id"])

	r = anon().get(path)

	assert_html(r, 200)
	assert _ids_listed(r)[:2] == [newer["id"], older["id"]]
	assert admin["username"] in element_text(r, f"action-{newer['id']}") and target in element_text(r, f"action-{older['id']}")


def test_an_entry_page_shows_that_entry():
	entry, target = _entry("ban_user")
	other, _ = _entry("ban_user")

	r = anon().get(f"/log/{entry['id']}")

	assert_html(r, 200)
	assert _ids_listed(r) == [entry["id"]] and target in element_text(r, f"action-{entry['id']}")


def test_the_admin_filter_lists_that_admins_entries_only():
	admin, other = factories.admin(2), factories.admin(2)
	mine = db.insert("modactions", user_id=admin["id"], kind="ban_user", target_user_id=factories.user()["id"])
	db.insert("modactions", user_id=other["id"], kind="ban_user", target_user_id=factories.user()["id"])

	r = anon().get("/log", params={"admin": admin["username"]})

	assert_html(r, 200)
	assert _ids_listed(r) == [mine["id"]]


def test_an_unknown_admin_is_not_found():
	assert_status(anon().get("/log", params={"admin": factories.unique("nobody")}), 404)


def test_the_kind_filter_lists_that_kind_only():
	ban, _ = _entry("ban_user")
	_entry("unban_user")

	r = anon().get("/log", params={"kind": "ban_user"})

	assert_html(r, 200)
	assert _ids_listed(r) == [ban["id"]]


@pytest.mark.parametrize("viewer, kind", [(anon, "no_such_kind"), (anon, "shadowban"), (lambda: as_user(factories.admin(2)), "no_such_kind"), (lambda: as_user(factories.admin(3)), "fallback")], ids=["unknown kind", "admin-only kind for a visitor", "unknown kind for an admin", "how unknown kinds show, for an admin"])
def test_a_kind_filter_that_cant_apply_is_ignored(viewer, kind):
	ban, _ = _entry("ban_user")
	unban, _ = _entry("unban_user")

	r = viewer().get("/log", params={"kind": kind})

	assert_html(r, 200)
	assert set(_ids_listed(r)) == {ban["id"], unban["id"]}


def _entry_as_written(kind):
	'''An entry of `kind` about a fresh target of the kind's sort, and what its page shows of that target (None for a site-wide kind).'''
	target = MOD_LOG_KINDS[kind].target
	columns, shown = {}, None
	if target == "user":
		user = factories.user()
		columns, shown = {"target_user_id": user["id"]}, user["username"]
	elif target == "post":
		post = factories.post(factories.user())
		columns, shown = {"target_submission_id": post["id"]}, f"/post/{post['id']}"
	elif target == "comment":
		comment = factories.comment(factories.user(), factories.post(factories.user()))
		columns, shown = {"target_comment_id": comment["id"]}, f"/comment/{comment['id']}"
	return db.insert("modactions", user_id=factories.admin(2)["id"], kind=kind, **columns), shown


@pytest.mark.parametrize("kind", MOD_LOG_KINDS)
def test_the_kind_filter_takes_every_kind_the_site_knows(kind):
	entry, _ = _entry_as_written(kind)
	_entry_as_written("ban_user" if kind != "ban_user" else "unban_user")

	r = as_user(factories.admin(3)).get("/log", params={"kind": kind})

	assert_html(r, 200)
	assert _ids_listed(r) == [entry["id"]]


@pytest.mark.parametrize("kind", MOD_LOG_KINDS)
def test_an_entry_shows_what_it_is_about(kind):
	entry, shown = _entry_as_written(kind)
	viewer = as_user(factories.admin(2)) if MOD_LOG_KINDS[kind].admin_only else anon()

	r = viewer.get(f"/log/{entry['id']}")

	assert_html(r, 200)
	if shown: assert_in_payload(r, shown)


def test_admins_filter_by_admin_only_kinds():
	shadowban, _ = _entry("shadowban")
	_entry("ban_user")

	r = as_user(factories.admin(2)).get("/log", params={"kind": "shadowban"})

	assert _ids_listed(r) == [shadowban["id"]]


@pytest.mark.parametrize("sender_shadowbanned", [False, True], ids=["", "shadowbanned sender"])
@pytest.mark.parametrize("viewer, sees", [("visitor", False), ("other user", False), ("sender", True), ("recipient", True), ("admin", True)])
def test_a_private_message_goes_unlinked_for_those_not_party_to_it(viewer, sees, sender_shadowbanned):
	sender, recipient = factories.user(shadowbanned="somemod" if sender_shadowbanned else None), factories.user()
	message = factories.message(sender, recipient)
	entry = db.insert("modactions", user_id=factories.admin(2)["id"], kind="remove_comment", target_comment_id=message["id"])
	client = {"visitor": anon, "other user": lambda: as_user(factories.user()), "sender": lambda: as_user(sender), "recipient": lambda: as_user(recipient), "admin": lambda: as_user(factories.admin(2))}[viewer]()

	r = client.get(f"/log/{entry['id']}")

	assert_html(r, 200)
	# A shadowbanned sender's messages reach only them and admins
	assert (f"/comment/{message['id']}" in r.text) == (sees and not (sender_shadowbanned and viewer == "recipient"))
