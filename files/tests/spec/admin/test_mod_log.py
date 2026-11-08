'''
The mod log: GET /log lists entries; GET /log/<id> shows one entry, and an id that isn't one written as a plain whole number is 404.

Some kinds of entry are shown only to admins (level 2+): shadowbanning and unshadowbanning, setting a post's flair, editing a post, linking alt accounts, and setting a user's filter mode. To anyone else (visitors, users below level 2, and API clients whatever their account's level) such an entry doesn't exist: the list leaves it out and its page is 404.

An entry names the post or comment it's about (a post by its title, both with a link to them), unless the viewer couldn't open it: a draft (or a comment on one), seen only by its author and admins from level 2, or a post or comment by a shadowbanned user, seen only by that user and admins from level 2. For anyone else the entry stays, saying only "post" or "comment", with no title or link. A ban's note, which links the post or comment the ban was for, follows the same rule.
'''
import pytest

from files.tests.spec.harness import *

ADMIN_ONLY_KINDS = ["shadowban", "unshadowban", "flair_post", "edit_post", "link_accounts", "filter_on", "filter_off", "filter_auto"]
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
HIDDEN_POSTS = {
	"draft": lambda: (factories.user(), {"private": True}),
	"shadowbanned author": lambda: (factories.user(shadowbanned="somemod"), {}),
}


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
	make_client, sees = TARGET_VIEWERS[viewer]

	r = make_client(author).get("/log")

	assert_html(r, 200)
	assert _shows_post(r, entry, post) == sees


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
	make_client, sees = TARGET_VIEWERS[viewer]

	r = make_client(author).get("/log")

	assert_html(r, 200)
	assert element_text(r, f"action-{entry['id']}")
	assert (f"/comment/{comment['id']}" in r.text) == (sees or hidden is None)


@pytest.mark.parametrize("viewer", ["visitor", "admin"])
@pytest.mark.parametrize("target", ["post", "comment"])
def test_a_bans_note_links_what_it_was_for_only_if_the_viewer_could_open_it(target, viewer):
	author = factories.user(shadowbanned="somemod")
	post = factories.post(author)
	item = post if target == "post" else factories.comment(author, post)
	db.insert("modactions", user_id=factories.admin(2)["id"], kind="ban_user", target_user_id=author["id"], **({"target_submission_id": post["id"]} if target == "post" else {"target_comment_id": item["id"]}))
	make_client, sees = TARGET_VIEWERS[viewer]

	r = make_client(author).get("/log")

	assert_html(r, 200)
	link = f"/post/{post['id']}" if target == "post" else f"/comment/{item['id']}"
	assert (link in r.text) == sees
