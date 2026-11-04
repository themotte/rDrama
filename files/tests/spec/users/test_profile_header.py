'''
What a profile page (GET /@<username>/ and /@<username>/posts) tells everyone about the user, above the listings:
- the user's bio, flair and friends text;
- while they're suspended, that they're banned, with the ban's reason;
- to admins (level 2 and up) only, the accounts linked to the user as alts.
'''
import time

import pytest

from files.tests.spec.harness import *

PAGES = ["/@{}/", "/@{}/posts"]


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("column", ["bio_html", "customtitle", "friends_html"])
def test_profile_shows_the_users_own_texts_to_everyone(page, column):
	token = factories.unique()
	user = factories.user(**{column: f"<p>{token}</p>" if column.endswith("_html") else token})

	r = anon().get(page.format(user["username"]))

	assert_html(r, 200)
	assert_in_payload(r, token)


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("unban_utc", [0, "future"], ids=["permanent", "temporary"])
def test_profile_of_a_suspended_user_shows_the_ban_reason(page, unban_utc):
	reason = factories.unique()
	user = factories.user(is_banned=factories.admin(2)["id"], ban_reason=reason, unban_utc=int(time.time()) + 86400 if unban_utc else 0)

	r = anon().get(page.format(user["username"]))

	assert_html(r, 200)
	assert_in_payload(r, reason)


@pytest.mark.parametrize("page", PAGES)
def test_profile_of_a_user_whose_ban_ran_out_shows_no_ban_reason(page):
	reason = factories.unique()
	user = factories.user(is_banned=factories.admin(2)["id"], ban_reason=reason, unban_utc=int(time.time()) - 60)

	r = anon().get(page.format(user["username"]))

	assert_html(r, 200)
	assert_not_in_payload(r, reason)


def _with_alt():
	user, alt = factories.user(), factories.user()
	db.insert("alts", user1=alt["id"], user2=user["id"], is_manual=False)
	return user, alt


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("level", [2, 3])
def test_profile_shows_alts_to_admins(page, level):
	user, alt = _with_alt()

	r = as_user(factories.admin(level)).get(page.format(user["username"]))

	assert_html(r, 200)
	assert_in_payload(r, alt["username"])


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("viewer", ["anonymous", "user", "level 1", "owner"])
def test_profile_hides_alts_from_everyone_else(page, viewer):
	user, alt = _with_alt()
	client = {"anonymous": anon, "user": lambda: as_user(factories.user()), "level 1": lambda: as_user(factories.admin(1)), "owner": lambda: as_user(user)}[viewer]()

	r = client.get(page.format(user["username"]))

	assert_html(r, 200)
	assert_not_in_payload(r, alt["username"])
