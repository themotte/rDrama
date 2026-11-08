'''
GET /blocks shows admins (level 2+) every block on the site: who blocks whom. Who may use it is pinned in test_access.
'''
from files.tests.spec.harness import *


def test_admins_see_every_block():
	pairs = [(factories.user(), factories.user()) for _ in range(2)]
	for blocker, blocked in pairs:
		db.insert("userblocks", user_id=blocker["id"], target_id=blocked["id"])

	r = as_user(factories.admin(2)).get("/blocks")

	assert_html(r, 200)
	# Each block reads as its blocker, then whom they block
	names = sorted((u["username"] for pair in pairs for u in pair), key=r.text.index)
	assert all(names.index(blocked["username"]) == names.index(blocker["username"]) + 1 for blocker, blocked in pairs), names
