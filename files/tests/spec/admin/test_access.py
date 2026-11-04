'''
Who may use the admin area at all. Each admin route requires a minimum admin level; this file pins only the refusals, and each feature's own tests show the route working at its minimal level.

Anonymous browsers are sent to log in, for pages and actions alike (an action's request body is not carried along). A logged-in account below the route's level is refused with 403, except the shadowbanned-users page, which answers 404 to anyone below level 2 as if it didn't exist. API clients are refused whatever their account's level (the shadowbanned-users page answers them 404 too): moderation happens in the browser. Refused requests change nothing.
'''
import pytest

from files.tests.spec.harness import *

# (method, path template, minimum admin level); the templates are filled from the rows `_targets` creates
ROUTES = [
	("POST", "/@{username}/make_admin", 3),
	("POST", "/@{username}/remove_admin", 3),
	("POST", "/@{username}/create_note", 2),
	("POST", "/@{username}/delete_note/{note_id}", 2),
	("POST", "/@{username}/revert_actions", 3),
	("GET", "/admin", 2),
	("POST", "/admin/site_settings/Signups", 3),
	("POST", "/admin/purge_cache", 3),
	("POST", "/admin/under_attack", 3),
	("POST", "/admin/dump_cache", 2),
	("GET", "/admin/filtered/posts", 2),
	("GET", "/admin/filtered/comments", 2),
	("POST", "/admin/update_filter_status", 2),
	("GET", "/admin/image_posts", 2),
	("GET", "/admin/reported/posts", 2),
	("GET", "/admin/reported/comments", 2),
	("GET", "/admin/removed/posts", 2),
	("GET", "/admin/removed/comments", 2),
	("GET", "/admin/users", 2),
	("GET", "/admin/alt_votes", 2),
	("POST", "/admin/link_accounts", 2),
	("POST", "/shadowban/{user_id}", 2),
	("POST", "/unshadowban/{user_id}", 2),
	("POST", "/filter_automatic/{user_id}", 2),
	("POST", "/filter_unfiltered/{user_id}", 2),
	("POST", "/filter_filtered/{user_id}", 2),
	("POST", "/admin/verify/{user_id}", 3),
	("POST", "/admin/unverify/{user_id}", 3),
	("POST", "/admin/title_change/{user_id}", 2),
	("POST", "/ban_user/{user_id}", 2),
	("POST", "/unban_user/{user_id}", 2),
	("POST", "/distinguish/{post_id}", 1),
	("POST", "/sticky/{post_id}", 2),
	("POST", "/unsticky/{post_id}", 2),
	("POST", "/distinguish_comment/{comment_id}", 1),
	("POST", "/sticky_comment/{comment_id}", 2),
	("POST", "/unsticky_comment/{comment_id}", 2),
	("GET", "/admin/banned_domains/", 3),
	("POST", "/admin/banned_domains", 3),
	("POST", "/admin/nuke_user", 3),
	("POST", "/admin/unnuke_user", 3),
	("GET", "/tasks/", 2),
	("GET", "/tasks/{task_id}/", 2),
	("GET", "/tasks/{task_id}/runs/", 2),
	("GET", "/tasks/{task_id}/runs/{run_id}", 2),
	("POST", "/tasks/{task_id}/schedule", 2),
	("GET", "/tasks/scheduled_posts/", 2),
	("POST", "/tasks/scheduled_posts/", 2),
	("GET", "/tasks/scheduled_posts/{scheduled_post_id}", 2),
	("POST", "/tasks/scheduled_posts/{scheduled_post_id}/content", 2),
	("POST", "/tasks/scheduled_posts/{scheduled_post_id}/schedule", 2),
]

SHADOWBANNED_PAGE = "/admin/shadowbanned"


def _route_id(route):
	method, path, _ = route
	return f"{method} {path}"


def _targets():
	'''Rows for every path parameter the admin routes take.'''
	admin = factories.admin(3)
	user = factories.user()
	post = factories.post(user)
	comment = factories.comment(user, post)
	note = db.insert("usernotes", author_id=admin["id"], reference_user=user["id"], note=factories.unique(), tag="Comment")
	task = db.insert("tasks_repeatable", author_id=admin["id"], type_id=1, enabled=False, run_state=1, frequency_day=0, time_of_day_utc="01:00", created_utc=1000)
	db.insert("tasks_repeatable_python", id=task["id"], import_path="files.helpers.config.const", callable="nothing")
	run = db.insert("tasks_repeatable_runs", task_id=task["id"], manual=False, created_utc=1000)
	scheduled_post = db.insert("tasks_repeatable", author_id=admin["id"], type_id=2, enabled=False, run_state=1, frequency_day=0, time_of_day_utc="01:00", created_utc=1000)
	db.insert("tasks_repeatable_scheduled_submissions", id=scheduled_post["id"], author_id_submission=admin["id"], ghost=False, private=False, over_18=False, is_bot=False, title="t", body="text", body_html="<p>text</p>")
	return {
		"username": user["username"],
		"user_id": user["id"],
		"post_id": post["id"],
		"comment_id": comment["id"],
		"note_id": note["id"],
		"task_id": task["id"],
		"run_id": run["id"],
		"scheduled_post_id": scheduled_post["id"],
	}


@pytest.mark.parametrize("route", ROUTES, ids=_route_id)
def test_anonymous_browsers_are_sent_to_log_in(route):
	method, template, _ = route
	path = template.format(**_targets())

	with db_diff() as d:
		r = anon().request(method, path)

	assert_login_redirect(r, returning_to=path)
	d.assert_exactly()


@pytest.mark.parametrize("route", ROUTES, ids=_route_id)
def test_accounts_below_the_routes_admin_level_are_forbidden(route):
	method, template, level = route
	path = template.format(**_targets())
	client = as_user(factories.admin(level - 1))

	with db_diff() as d:
		r = client.get(path) if method == "GET" else client.post(path)

	assert_status(r, 403)
	d.assert_exactly()


@pytest.mark.parametrize("route", ROUTES, ids=_route_id)
def test_api_clients_are_forbidden_whatever_their_level(route):
	method, template, _ = route
	path = template.format(**_targets())
	client = as_api(factories.api_token(factories.admin(3)))

	with db_diff() as d:
		r = client.request(method, path)

	assert_status(r, 403)
	d.assert_exactly()


def test_the_shadowbanned_users_page_does_not_exist_for_api_clients():
	client = as_api(factories.api_token(factories.admin(3)))

	assert_status(client.get(SHADOWBANNED_PAGE), 404)


def test_anonymous_browsers_are_sent_to_log_in_from_the_shadowbanned_users_page():
	assert_login_redirect(anon().get(SHADOWBANNED_PAGE), returning_to=SHADOWBANNED_PAGE)


def test_the_shadowbanned_users_page_does_not_exist_below_admin_level_2():
	client = as_user(factories.admin(1))

	with db_diff() as d:
		r = client.get(SHADOWBANNED_PAGE)

	assert_status(r, 404)
	d.assert_exactly()
