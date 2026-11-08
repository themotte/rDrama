'''
The mod log: GET /log/<id> shows one entry.

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
