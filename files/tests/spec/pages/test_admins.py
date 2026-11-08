'''
GET /admins lists the site's admins, open to everyone: accounts of admin level 2 and up first, then those of level 1, each group by truescore, highest first. Each admin's entry shows (in the element with id "mod-actions-<user id>") how many mod-log entries they made that the viewer could see in the mod log: entries only admins see count only for admins.
'''
import pytest

from files.tests.spec.harness import *


def _admin_with_entries():
	'''A level-2 admin with two entries anyone sees and one only admins see.'''
	admin = factories.admin(2)
	for kind in ("ban_user", "unban_user", "shadowban"):
		db.insert("modactions", user_id=admin["id"], kind=kind, target_user_id=factories.user()["id"])
	return admin


@pytest.mark.parametrize("viewer, count", [(anon, "2"), (lambda: as_user(factories.user()), "2"), (lambda: as_api(factories.api_token(factories.admin(3))), "2"), (lambda: as_user(factories.admin(2)), "3")], ids=["visitor", "user", "admin's API client", "admin"])
def test_each_admin_shows_the_entries_the_viewer_could_see(viewer, count):
	admin = _admin_with_entries()

	r = viewer().get("/admins")

	assert_html(r, 200)
	assert element_text(r, f"mod-actions-{admin['id']}") == count


@pytest.mark.parametrize("viewer", [anon, lambda: as_user(factories.admin(3))], ids=["visitor", "head admin"])
def test_admins_from_level_2_come_first_each_group_by_truescore(viewer):
	low_2, high_2 = factories.admin(2, truescore=10), factories.admin(3, truescore=20)
	low_1, high_1 = factories.admin(1, truescore=30), factories.admin(1, truescore=40)

	r = viewer().get("/admins")

	assert_in_order(r, [f'"mod-actions-{u["id"]}"' for u in (high_2, low_2, high_1, low_1)])


def test_accounts_without_an_admin_level_arent_listed():
	user, admin = factories.user(), factories.admin(1)

	r = anon().get("/admins")

	assert_in_payload(r, admin["username"])
	assert_not_in_payload(r, user["username"])
