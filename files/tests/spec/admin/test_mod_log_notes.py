'''
What admins type into their actions (ban reasons, flair, banned domains and their reasons) appears in the public mod log (GET /log) as text: markup in it is shown, never interpreted.
'''
import pytest

from files.tests.spec.harness import *




def _ban(markup):
	user = factories.user()
	as_user(factories.admin(2)).post(f"/ban_user/{user['id']}", {"reason": markup})


def _flair(markup):
	user = factories.user()
	as_user(factories.admin(2)).post(f"/admin/title_change/{user['id']}", {"title": markup})


def _banned_domain(markup):
	as_user(factories.admin(3)).post("/admin/banned_domains", {"domain": f"{factories.unique('d')}.example.com", "reason": markup})


@pytest.mark.parametrize("act", [_ban, _flair, _banned_domain], ids=["ban reason", "flair", "banned domain reason"])
def test_admin_text_in_the_mod_log_is_shown_as_text(act):
	token = factories.unique("markup")
	markup = f"<b id={token}>"
	act(markup)

	r = as_user(factories.admin(3)).get("/log")

	assert_html(r, 200)
	assert_in_payload(r, token)
	assert_not_in_payload(r, markup)
