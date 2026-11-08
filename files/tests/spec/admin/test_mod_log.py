'''
The mod log: GET /log/<id> shows one entry; an id that isn't one written as a plain whole number is 404.

Some kinds of entry are shown only to admins (level 2+): shadowbanning and unshadowbanning, setting a post's flair and editing a post. To anyone else (visitors, users below level 2, and API clients whatever their account's level) such an entry doesn't exist: 404.
'''
import pytest

from files.tests.spec.harness import *

ADMIN_ONLY_KINDS = ["shadowban", "unshadowban", "flair_post", "edit_post"]
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
