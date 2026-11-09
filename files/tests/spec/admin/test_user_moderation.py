'''
Admin actions on a user account, all POSTs taking the user's id in the path, plus two admin listings of users:
- /shadowban/<id> hides the user's content from everyone but them and moderators; /unshadowban/<id> lifts that (and the ban-evasion mark). System accounts and admins can't be shadowbanned. Level-3 admins other than the actor are told of each shadowban.
- /filter_automatic/<id>, /filter_unfiltered/<id>, /filter_filtered/<id> set whether the user's new content waits in the filter queue: decided per item, never, or always.
- /admin/verify/<id> and /admin/unverify/<id> (level 3) set or clear the account's verified mark.
- /admin/title_change/<id> sets the user's flair from "title" (surrounding whitespace dropped, cut to 100 characters as users' own flair is); a non-empty "locked" stops the user changing it. Redirects to the profile.
- /ban_user/<id> bans for "days" (temporary; absent, empty or 0 means permanent; at most 3650 and ending before 2038, when the stored end time runs out, else 400) with an optional "reason". A reason beginning "/post/<id>" or "/comment/<id>" marks that post or comment as the one the user was banned for. A non-empty "alts" bans the user's linked accounts too. The user is notified, and so are level-3 admins other than the actor. With "redir" present it redirects to the profile, else answers JSON. System accounts and users at or above the actor's level can't be banned.
- /unban_user/<id> lifts a ban and notifies the user; from the user's profile page (by Referer) it redirects back there, else answers JSON.
- GET /admin/users lists non-banned accounts, newest first, 25 to a page ("page"); GET /admin/shadowbanned lists shadowbanned accounts, and doesn't exist for non-admins.

Every action is logged in the mod log as a `modactions` row of the listed kind naming the actor and the target user. An id that isn't an existing account's is 404; a missing required field is 400.
'''
import time

import pytest

from files.tests.spec.harness import *

# A flair lock has no practical end: its expiry lies years ahead
FLAIR_LOCK_HORIZON = 10 * 365 * 86400


def _unknown_user_id():
	return db.execute("SELECT nextval('users_id_seq')")


def _profile(user):
	return f"/@{user['username']}"


def _mod_action(kind, actor, target, **columns):
	return {"kind": kind, "user_id": actor["id"], "target_user_id": target["id"], "target_submission_id": None, "target_comment_id": None, **columns}


def _notice(d, user):
	'''The new notification message `user` received in diff `d`.'''
	[notification] = [n for n in d.inserted["notifications"] if n["user_id"] == user["id"]]
	[message] = [c for c in d.inserted["comments"] if c["id"] == notification["comment_id"]]
	return message


SYSTEM_MESSAGE = {"author_id": seed.SYSTEM_ID, "parent_submission": None, "level": 1, "state_mod": "VISIBLE"}


USER_ACTIONS = ["/shadowban", "/unshadowban", "/filter_automatic", "/filter_unfiltered", "/filter_filtered", "/admin/verify", "/admin/unverify", "/admin/title_change", "/ban_user", "/unban_user"]


@pytest.mark.parametrize("action", USER_ACTIONS)
@pytest.mark.parametrize("user_id", ["unknown", "someone", "99999999999", "0"])
def test_an_action_on_no_existing_account_is_not_found(action, user_id):
	client = as_user(factories.admin(3))
	if user_id == "unknown": user_id = _unknown_user_id()

	with db_diff() as d:
		r = client.post(f"{action}/{user_id}", {"title": factories.unique(), "reason": factories.unique()}, headers=XHR)

	assert_status(r, 404)
	d.assert_exactly()


def test_a_flair_change_without_a_title_is_refused():
	user = factories.user()
	client = as_user(factories.admin(2))

	with db_diff() as d:
		r = client.post(f"/admin/title_change/{user['id']}", headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


# Shadowbans

def test_admin_shadowbans_a_user_and_tells_the_other_head_admins():
	actor, other_head, junior = factories.admin(3), factories.admin(3), factories.admin(2)
	user = factories.user()

	with db_diff() as d:
		r = as_user(actor).post(f"/shadowban/{user['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"users": {user["id"]: {"shadowbanned": actor["username"]}}},
		inserted={
			"modactions": [_mod_action("shadowban", actor, user)],
			"comments": [SYSTEM_MESSAGE],
			"notifications": [{"user_id": other_head["id"]}],
		},
	)
	assert user["username"] in _notice(d, other_head)["body_html"]


@pytest.mark.parametrize("system_id", [seed.SYSTEM_ID, seed.AUTOJANNY_ID], ids=["System", "AutoJanny"])
def test_system_accounts_cannot_be_shadowbanned(system_id):
	actor = factories.admin(3)

	with db_diff() as d:
		r = as_user(actor).post(f"/shadowban/{system_id}", headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("level", [1, 3])
def test_admins_cannot_be_shadowbanned(level):
	actor, target = factories.admin(3), factories.admin(level)

	with db_diff() as d:
		r = as_user(actor).post(f"/shadowban/{target['id']}", headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


def test_shadowbanning_an_unknown_user_is_not_found():
	actor = factories.admin(2)

	assert_status(as_user(actor).post(f"/shadowban/{_unknown_user_id()}", headers=XHR), 404)


def test_admin_lifts_a_shadowban_and_the_ban_evasion_mark():
	actor = factories.admin(2)
	user = factories.user(shadowbanned="AutoJanny", ban_evade=1)

	with db_diff() as d:
		r = as_user(actor).post(f"/unshadowban/{user['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"users": {user["id"]: {"shadowbanned": None, "ban_evade": 0}}},
		inserted={"modactions": [_mod_action("unshadowban", actor, user)]},
	)


# Filter modes

@pytest.mark.parametrize("action, behavior, kind, before", [
	("filter_automatic", "AUTOMATIC", "filter_auto", "FILTERED"),
	("filter_unfiltered", "UNFILTERED", "filter_off", "AUTOMATIC"),
	("filter_filtered", "FILTERED", "filter_on", "AUTOMATIC"),
])
def test_admin_sets_a_users_filter_mode(action, behavior, kind, before):
	actor = factories.admin(2)
	user = factories.user(filter_behavior=before)

	with db_diff() as d:
		r = as_user(actor).post(f"/{action}/{user['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"users": {user["id"]: {"filter_behavior": behavior}}},
		inserted={"modactions": [_mod_action(kind, actor, user)]},
	)


# Verification

def test_head_admin_verifies_a_user():
	actor = factories.admin(3)
	user = factories.user(verified=None)

	with db_diff() as d:
		r = as_user(actor).post(f"/admin/verify/{user['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"users": {user["id"]: {"verified": "Verified"}}},
		inserted={"modactions": [_mod_action("check", actor, user)]},
	)


def test_head_admin_unverifies_a_user():
	actor = factories.admin(3)
	user = factories.user(verified="Verified")

	with db_diff() as d:
		r = as_user(actor).post(f"/admin/unverify/{user['id']}")

	assert_json_message(r)
	d.assert_exactly(
		updated={"users": {user["id"]: {"verified": None}}},
		inserted={"modactions": [_mod_action("uncheck", actor, user)]},
	)


# Flair

def test_admin_sets_a_locked_flair():
	actor = factories.admin(2)
	user = factories.user()
	title = factories.unique("flair")

	with db_diff() as d:
		r = as_user(actor).post(f"/admin/title_change/{user['id']}", {"title": f"  {title} ", "locked": "on"})

	assert_redirect(r, _profile(user))
	d.assert_exactly(
		updated={"users": {user["id"]: {"customtitleplain": title, "customtitle": title, "flairchanged": ANY}}},
		inserted={"modactions": [_mod_action("set_flair_locked", actor, user, _note=ANY)]},
	)
	assert db.row("users", id=user["id"])["flairchanged"] > time.time() + FLAIR_LOCK_HORIZON
	assert title in d.inserted["modactions"][0]["_note"]


def test_flair_shows_on_the_profile_as_text():
	user = factories.user()
	token = factories.unique("markup")
	markup = f"<b id={token}>"
	as_user(factories.admin(2)).post(f"/admin/title_change/{user['id']}", {"title": markup})

	r = anon().get(_profile(user))

	assert_html(r, 200)
	assert_in_payload(r, token)
	assert_not_in_payload(r, markup)


def test_a_long_flair_is_cut_to_100_characters():
	actor = factories.admin(2)
	user = factories.user()
	title = factories.unique("flair").ljust(150, "x")

	with db_diff() as d:
		r = as_user(actor).post(f"/admin/title_change/{user['id']}", {"title": title})

	assert_redirect(r, _profile(user))
	d.assert_exactly(
		updated={"users": {user["id"]: {"customtitleplain": title[:100], "customtitle": title[:100]}}},
		inserted={"modactions": [_mod_action("set_flair_notlocked", actor, user, _note=ANY)]},
	)


def test_admin_sets_an_unlocked_flair_lifting_a_lock():
	actor = factories.admin(2)
	user = factories.user(flairchanged=int(time.time()) + 86400)
	title = factories.unique("flair")

	with db_diff() as d:
		r = as_user(actor).post(f"/admin/title_change/{user['id']}", {"title": title})

	assert_redirect(r, _profile(user))
	d.assert_exactly(
		updated={"users": {user["id"]: {"customtitleplain": title, "customtitle": title, "flairchanged": None}}},
		inserted={"modactions": [_mod_action("set_flair_notlocked", actor, user, _note=ANY)]},
	)
	assert title in d.inserted["modactions"][0]["_note"]


# Bans

def _ban_changes(actor, user, user_changes, *, notified, updated=None):
	'''The changes a ban of `user` makes: `user_changes` to `user` (plus `updated`), the mod action, and two messages, one for the user and one for the head admins, between them delivered to `notified`.'''
	return {
		"updated": {"users": {user["id"]: user_changes}, **(updated or {})},
		"inserted": {
			"modactions": [_mod_action("ban_user", actor, user, _note=ANY)],
			"comments": [SYSTEM_MESSAGE, SYSTEM_MESSAGE],
			"notifications": [{"user_id": u["id"]} for u in notified],
		},
	}


def _ban(actor, user, data, headers=None):
	with db_diff() as d:
		r = as_user(actor).post(f"/ban_user/{user['id']}", data, headers=headers)
	return r, d


def test_admin_bans_a_user_for_some_days_and_everyone_concerned_is_told():
	actor, other_head = factories.admin(3), factories.admin(3)
	user = factories.user()
	reason = factories.unique("reason")
	before = int(time.time())

	r, d = _ban(actor, user, {"days": "3", "reason": reason})

	after = int(time.time())
	assert_json_message(r)
	d.assert_exactly(**_ban_changes(actor, user, {"is_banned": actor["id"], "unban_utc": ANY, "ban_reason": reason}, notified=[user, other_head]))
	assert before + 3 * 86400 <= db.row("users", id=user["id"])["unban_utc"] <= after + 3 * 86400 + 1
	assert reason in d.inserted["modactions"][0]["_note"]
	assert reason in _notice(d, user)["body_html"]
	assert user["username"] in _notice(d, other_head)["body_html"]


def test_admin_bans_a_user_permanently_without_a_reason():
	actor = factories.admin(2)
	user = factories.user()

	r, d = _ban(actor, user, {"days": ""})

	assert_json_message(r)
	d.assert_exactly(**_ban_changes(actor, user, {"is_banned": actor["id"]}, notified=[user]))


def test_head_admin_bans_a_lower_admin():
	actor, target = factories.admin(3), factories.admin(2)

	r, d = _ban(actor, target, {})

	assert_json_message(r)
	d.assert_exactly(**_ban_changes(actor, target, {"is_banned": actor["id"]}, notified=[target]))


def test_banning_from_the_profile_returns_there():
	actor = factories.admin(2)
	user = factories.user()

	r, d = _ban(actor, user, {"redir": ""})

	assert_redirect(r, _profile(user))
	d.assert_exactly(**_ban_changes(actor, user, {"is_banned": actor["id"]}, notified=[user]))


@pytest.mark.parametrize("kind", ["post", "comment"])
def test_a_ban_reason_naming_a_post_or_comment_marks_it(kind):
	actor = factories.admin(2)
	author = factories.user()
	post = factories.post(author)
	item = post if kind == "post" else factories.comment(author, post)
	table = "submissions" if kind == "post" else "comments"
	reason = f"/{kind}/{item['id']} {factories.unique('reason')}"

	r, d = _ban(actor, author, {"reason": reason})

	assert_json_message(r)
	d.assert_exactly(**_ban_changes(actor, author, {"is_banned": actor["id"], "ban_reason": reason}, notified=[author], updated={table: {item["id"]: {"bannedfor": True}}}))


@pytest.mark.parametrize("orientation", ["user first", "alt first"])
def test_banning_with_alts_bans_the_linked_accounts_too(orientation):
	actor = factories.admin(2)
	user, alt = factories.user(), factories.user()
	first, second = (user, alt) if orientation == "user first" else (alt, user)
	db.insert("alts", user1=first["id"], user2=second["id"], is_manual=True)
	reason = factories.unique("reason")

	r, d = _ban(actor, user, {"days": "2", "reason": reason, "alts": "on"})

	assert_json_message(r)
	banned = {"is_banned": actor["id"], "unban_utc": ANY, "ban_reason": reason}
	d.assert_exactly(**_ban_changes(actor, user, banned, notified=[user], updated={"users": {user["id"]: banned, alt["id"]: banned}}))
	assert db.row("users", id=alt["id"])["unban_utc"] == db.row("users", id=user["id"])["unban_utc"]


def test_banning_without_alts_leaves_the_linked_accounts_alone():
	actor = factories.admin(2)
	user, alt = factories.user(), factories.user()
	db.insert("alts", user1=user["id"], user2=alt["id"], is_manual=True)

	r, d = _ban(actor, user, {})

	assert_json_message(r)
	d.assert_exactly(**_ban_changes(actor, user, {"is_banned": actor["id"]}, notified=[user]))


def test_banning_with_alts_skips_admin_alts():
	actor = factories.admin(3)
	user = factories.user()
	admin_alt, alt = factories.admin(2, username=factories.unique("a")), factories.user(username=factories.unique("z"))
	for linked in (admin_alt, alt):
		db.insert("alts", user1=user["id"], user2=linked["id"], is_manual=True)

	r, d = _ban(actor, user, {"alts": "on"})

	assert_json_message(r)
	banned = {"is_banned": actor["id"]}
	d.assert_exactly(**_ban_changes(actor, user, banned, notified=[user], updated={"users": {user["id"]: banned, alt["id"]: banned}}))


def test_a_ban_takes_a_reason_of_up_to_256_characters():
	actor = factories.admin(2)
	user = factories.user()
	reason = factories.unique("reason").ljust(300, "x")

	r, d = _ban(actor, user, {"days": "1", "reason": reason})

	assert_json_message(r)
	d.assert_exactly(**_ban_changes(actor, user, {"is_banned": actor["id"], "unban_utc": ANY, "ban_reason": reason[:256]}, notified=[user]))


def test_a_ban_reason_is_stored_escaped_however_long_that_makes_it():
	actor = factories.admin(2)
	user = factories.user()

	r, d = _ban(actor, user, {"days": "1", "reason": "&" * 300})

	assert_json_message(r)
	d.assert_exactly(**_ban_changes(actor, user, {"is_banned": actor["id"], "unban_utc": ANY, "ban_reason": "&amp;" * 256}, notified=[user]))


def test_a_ban_reason_is_shown_on_the_profile_as_text():
	actor = factories.admin(2)
	user = factories.user()
	token = factories.unique("markup")
	markup = f"<b id={token}>"
	as_user(actor).post(f"/ban_user/{user['id']}", {"reason": "&" * 60 + markup})

	r = anon().get(_profile(user))

	assert_html(r, 200)
	assert_not_in_payload(r, markup)


def test_a_permanent_ban_replaces_a_temporary_one():
	actor = factories.admin(2)
	user = factories.user(is_banned=actor["id"], unban_utc=int(time.time()) + 86400, ban_reason=factories.unique("reason"))
	reason = factories.unique("reason")

	r, d = _ban(actor, user, {"reason": reason})

	assert_json_message(r)
	d.assert_exactly(**_ban_changes(actor, user, {"unban_utc": 0, "ban_reason": reason}, notified=[user]))


def test_a_ban_without_a_reason_clears_the_previous_reason():
	actor = factories.admin(2)
	user = factories.user(is_banned=actor["id"], ban_reason=factories.unique("reason"))

	r, d = _ban(actor, user, {})

	assert_json_message(r)
	d.assert_exactly(**_ban_changes(actor, user, {"ban_reason": None}, notified=[user]))


def test_a_ban_may_last_a_year():
	actor = factories.admin(2)
	user = factories.user()

	r, d = _ban(actor, user, {"days": "365"})

	assert_json_message(r)
	d.assert_exactly(**_ban_changes(actor, user, {"is_banned": actor["id"], "unban_utc": ANY}, notified=[user]))


@pytest.mark.parametrize("days", ["soon", "-1", "nan", "inf", "3651", "past 2038"])
def test_a_ban_must_last_a_number_of_days_from_0_to_ten_years_ending_before_2038(days):
	actor = factories.admin(2)
	user = factories.user()
	if days == "past 2038": days = str((2**31 - int(time.time())) / 86400 + 0.01)

	r, d = _ban(actor, user, {"days": days}, headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


@pytest.mark.parametrize("reason", ["/post/{unknown}", "/post/many", "/comment/{unknown} spam", "/comment/"])
def test_a_ban_reason_naming_no_existing_post_or_comment_marks_nothing(reason):
	actor = factories.admin(2)
	user = factories.user()
	reason = reason.format(unknown=db.execute("SELECT nextval('submissions_id_seq')") + 1000)

	r, d = _ban(actor, user, {"reason": reason})

	assert_json_message(r)
	d.assert_exactly(**_ban_changes(actor, user, {"is_banned": actor["id"], "ban_reason": reason}, notified=[user]))


@pytest.mark.parametrize("system_id", [seed.SYSTEM_ID, seed.AUTOJANNY_ID], ids=["System", "AutoJanny"])
def test_system_accounts_cannot_be_banned(system_id):
	actor = factories.admin(3)

	with db_diff() as d:
		r = as_user(actor).post(f"/ban_user/{system_id}", {"reason": factories.unique("reason")}, headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("actor_level, target_level", [(2, 2), (2, 3), (3, 3)])
def test_users_at_or_above_the_admins_level_cannot_be_banned(actor_level, target_level):
	actor, target = factories.admin(actor_level), factories.admin(target_level)

	r, d = _ban(actor, target, {"reason": factories.unique("reason")}, headers=XHR)

	assert_status(r, 403)
	d.assert_exactly()


def test_banning_an_unknown_user_is_not_found():
	actor = factories.admin(2)

	assert_status(as_user(actor).post(f"/ban_user/{_unknown_user_id()}", headers=XHR), 404)


# Unbans

def _unban_changes(actor, user):
	return {
		"updated": {"users": {user["id"]: {"is_banned": 0, "unban_utc": 0, "ban_evade": 0, "ban_reason": None}}},
		"inserted": {
			"modactions": [_mod_action("unban_user", actor, user)],
			"comments": [SYSTEM_MESSAGE],
			"notifications": [{"user_id": user["id"]}],
		},
	}


def _banned_user(actor):
	return factories.user(is_banned=actor["id"], unban_utc=int(time.time()) + 86400, ban_evade=1, ban_reason=factories.unique("reason"))


def test_admin_unbans_a_user_and_tells_them():
	actor = factories.admin(2)
	user = _banned_user(actor)

	with db_diff() as d:
		r = as_user(actor).post(f"/unban_user/{user['id']}")

	assert_json_message(r)
	d.assert_exactly(**_unban_changes(actor, user))


def test_unbanning_from_the_profile_returns_there():
	actor = factories.admin(2)
	user = _banned_user(actor)

	with db_diff() as d:
		r = as_user(actor).post(f"/unban_user/{user['id']}", headers={"Referer": f"{config.site_url()}{_profile(user)}"})

	assert_redirect(r, _profile(user))
	d.assert_exactly(**_unban_changes(actor, user))


def test_unbanning_a_user_who_is_not_banned_is_refused():
	actor = factories.admin(2)
	user = factories.user()

	with db_diff() as d:
		r = as_user(actor).post(f"/unban_user/{user['id']}", headers=XHR)

	assert_status(r, 400)
	d.assert_exactly()


# Listings

def test_user_list_shows_non_banned_accounts_newest_first_25_to_a_page():
	admin = factories.admin(2, created_utc=1000)
	base = int(time.time()) + 1000
	users = [factories.user(created_utc=base + i) for i in range(26)]
	banned = factories.user(created_utc=base + 100, is_banned=admin["id"])
	client = as_user(admin)

	first, second = client.get("/admin/users"), client.get("/admin/users", params={"page": "2"})

	assert_html(first, 200)
	for u in users[1:]:
		assert_in_payload(first, u["username"])
	assert_not_in_payload(first, users[0]["username"])
	assert_not_in_payload(first, banned["username"])
	assert_in_payload(second, users[0]["username"])
	assert_not_in_payload(second, users[1]["username"])


def test_shadowbanned_list_shows_shadowbanned_accounts():
	admin = factories.admin(2)
	shadowbanned, regular = factories.user(shadowbanned="AutoJanny"), factories.user()

	r = as_user(admin).get("/admin/shadowbanned")

	assert_html(r, 200)
	assert_in_payload(r, shadowbanned["username"])
	assert_not_in_payload(r, regular["username"])


@pytest.mark.parametrize("level", [0, 1])
def test_shadowbanned_list_does_not_exist_for_non_admins(level):
	factories.user(shadowbanned="AutoJanny")

	assert_status(as_user(factories.admin(level)).get("/admin/shadowbanned"), 404)

