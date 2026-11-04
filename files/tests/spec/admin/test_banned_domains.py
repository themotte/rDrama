'''
Banned domains, whose links can't be submitted (see spec/posts/test_submit), managed by level-3 admins:
- GET /admin/banned_domains/ lists every banned domain with its reason.
- POST /admin/banned_domains with "domain" and "reason" bans the domain, or, if it is already banned, unbans it (the reason is then ignored). Either way it logs a mod action and sends the browser back to the list. Surrounding whitespace is trimmed from both fields; a missing or blank domain is 400.
'''
import pytest

from files.tests.spec.harness import *

LIST = "/admin/banned_domains/"


def _domain():
	return f"{factories.unique('domain')}.example"


def test_the_list_shows_each_banned_domain_with_its_reason():
	domain, reason = _domain(), factories.unique("reason")
	db.insert("banneddomains", domain=domain, reason=reason)

	r = as_user(factories.admin(3)).get(LIST)

	assert_html(r, 200)
	assert_in_payload(r, domain)
	assert_in_payload(r, reason)


def test_admin_bans_a_domain_with_a_reason():
	admin = factories.admin(3)
	domain, reason = _domain(), factories.unique("reason")
	client = as_user(admin)

	with db_diff() as d:
		r = client.post("/admin/banned_domains", {"domain": f" {domain} ", "reason": f" {reason} "})

	assert_redirect(r, LIST)
	d.assert_exactly(inserted={
		"banneddomains": [{"domain": domain, "reason": reason}],
		"modactions": [{"kind": "ban_domain", "user_id": admin["id"], "target_user_id": None, "target_submission_id": None, "target_comment_id": None}],
	})
	note = d.inserted["modactions"][0]["_note"]
	assert domain in note and reason in note, note


def test_submitting_an_already_banned_domain_unbans_it():
	admin = factories.admin(3)
	domain = _domain()
	db.insert("banneddomains", domain=domain, reason=factories.unique("reason"))
	client = as_user(admin)

	with db_diff() as d:
		r = client.post("/admin/banned_domains", {"domain": domain, "reason": factories.unique("reason")})

	assert_redirect(r, LIST)
	d.assert_exactly(
		deleted={"banneddomains": [domain]},
		inserted={"modactions": [{"kind": "unban_domain", "user_id": admin["id"], "_note": domain, "target_user_id": None, "target_submission_id": None, "target_comment_id": None}]},
	)


@pytest.mark.parametrize("form", [{}, {"domain": ""}, {"domain": "   "}], ids=["missing", "empty", "blank"])
def test_a_domain_is_required(form):
	client = as_user(factories.admin(3))

	with db_diff() as d:
		r = client.post("/admin/banned_domains", {**form, "reason": factories.unique("reason")})

	assert_status(r, 400)
	d.assert_exactly()
