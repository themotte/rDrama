'''
Every route the site answers: its method, its path, who may use it and whether API clients may. This is specification content, kept in the harness so the spec's route cells and the checks that keep the table complete can share it.

Paths are written with these variables:
- `<id>`: a row id, written in ASCII digits without a leading zero, from 1 to 2147483647 (2**31 - 1); anything else there is 404 (spec/routes), for everyone, before any gate. Ids sent in a query or a form are read by the rules of the route's area;
- `<text>`: any text without a "/", at least one character;
- `<path>`: any text, "/" included, at least one character, not starting with "/";
- `<a|b>`: one of the words listed.

Where a path matches more than one row, a row with fixed text where the other has a variable wins (GET /@me isn't the profile of a user "me"). A trailing "/" is optional on every path; none is written here. Doubled "/" inside a path are redirected (308) to the path with them merged. A path the table doesn't list is 404, and a method a listed path doesn't take is 405. HEAD is answered for every GET row as GET would be, without the body, and OPTIONS for every path, listing its methods (spec/routes).

A request is checked in this order:
1. The checks every request gets: a query that isn't UTF-8 (400); the Host (403 unless the site's own); while the Bots site setting is off, any Authorization header (403); a missing User-Agent (403); read-only mode, which refuses changes from all but admins, logging in aside (auth/test_session).
2. The path and method, as above.
3. The route's gate (`access`), which answers before anything the path names is looked up, so a refused request learns nothing about it:
   - PUBLIC: open to everyone, and the login isn't read, so the request is answered the same logged in or not (read-only mode aside), and a browser arriving without a session isn't given one (unless the route is there to write the session);
   - ANYONE: open to everyone, served as the logged-in member when there is one (a POST without that member's form key is served as logged out). A browser arriving without a session is given one, as at every gate below;
   - USER: logged-in members only; anyone else is sent to log in (asserts.assert_login_redirect), including a member's POST without their form key, except that API clients and xhr requests get 401 with a JSON error (asserts.assert_api_unauthorized);
   - USER_NOT_PERMABANNED: as USER, and a permanently suspended member is refused with 403;
   - admin(n): as USER, and a member below admin level n is refused with 403.
4. API clients (`api_clients` False): refused with 403 where the route is only for the member's own browser, and on every admin route. The routes they may use serve them as their holder's browser (users/test_api_clients).
5. The route's own rules, in the spec files for its area. Some of those are refusals of their own, such as search refusing known crawlers' User-Agents.

spec/routes checks each gate from below, with values that name nothing; that a route serves those it should, at the lowest level it allows, is in the spec files for its area.

The table describes the site as the spec runs it. The admins' request-performance controls under /performance/ are outside the spec, as are the routes a developer mode and the request profiler add.
'''
from typing import NamedTuple

PUBLIC = "public"
ANYONE = "anyone"
USER = "user"
USER_NOT_PERMABANNED = "user not permanently suspended"


def admin(level: int) -> str:
	return f"admin {level}"


def admin_level(access: str) -> int | None:
	'''The admin level an `access` value requires, if it is admin(n).'''
	return int(access.removeprefix("admin ")) if access.startswith("admin ") else None


class Route(NamedTuple):
	method: str
	path: str
	access: str
	api_clients: bool


# Sorted by path, then method
ROUTES = [
	Route("GET", "/", ANYONE, True),
	Route("GET", "/2faqr/<text>", USER, True),
	Route("GET", "/<id>/info", USER, True),
	Route("GET", "/@<text>", ANYONE, True),
	Route("GET", "/@<text>/<upvoters|downvoters|upvoting|downvoting>", admin(3), False),
	Route("GET", "/@<text>/<upvoters|downvoters|upvoting|downvoting>/<id>/<posts|comments>", admin(3), False),
	Route("POST", "/@<text>/create_note", admin(2), False),
	Route("POST", "/@<text>/delete_note/<id>", admin(2), False),
	Route("GET", "/@<text>/followers", ANYONE, True),
	Route("GET", "/@<text>/following", ANYONE, True),
	Route("GET", "/@<text>/info", USER, True),
	Route("POST", "/@<text>/make_admin", admin(3), False),
	Route("POST", "/@<text>/message", USER, True),
	Route("GET", "/@<text>/pic", PUBLIC, True),
	Route("GET", "/@<text>/posts", ANYONE, True),
	Route("GET", "/@<text>/profilecss", PUBLIC, True),
	Route("POST", "/@<text>/remove_admin", admin(3), False),
	Route("POST", "/@<text>/revert_actions", admin(3), False),
	Route("GET", "/@<text>/saved/comments", USER, True),
	Route("GET", "/@<text>/saved/posts", USER, True),
	Route("GET", "/@me", USER, True),
	Route("GET", "/activate", USER, True),
	Route("GET", "/admin", admin(2), False),
	Route("GET", "/admin/alt_votes", admin(2), False),
	Route("GET", "/admin/app/<id>", admin(2), False),
	Route("GET", "/admin/app/<id>/comments", admin(2), False),
	Route("POST", "/admin/app/approve/<id>", admin(3), False),
	Route("POST", "/admin/app/reject/<id>", admin(2), False),
	Route("POST", "/admin/app/revoke/<id>", admin(2), False),
	Route("GET", "/admin/apps", admin(2), False),
	Route("GET", "/admin/banned_domains", admin(3), False),
	Route("POST", "/admin/banned_domains", admin(3), False),
	Route("POST", "/admin/dump_cache", admin(2), False),
	Route("GET", "/admin/filtered/comments", admin(2), False),
	Route("GET", "/admin/filtered/posts", admin(2), False),
	Route("GET", "/admin/image_posts", admin(2), False),
	Route("POST", "/admin/link_accounts", admin(2), False),
	Route("POST", "/admin/nuke_user", admin(3), False),
	Route("POST", "/admin/purge_cache", admin(3), False),
	Route("GET", "/admin/removed/comments", admin(2), False),
	Route("GET", "/admin/removed/posts", admin(2), False),
	Route("GET", "/admin/reported/comments", admin(2), False),
	Route("GET", "/admin/reported/posts", admin(2), False),
	Route("GET", "/admin/shadowbanned", admin(2), False),
	Route("POST", "/admin/site_settings/<text>", admin(3), False),
	Route("POST", "/admin/title_change/<id>", admin(2), False),
	Route("POST", "/admin/under_attack", admin(3), False),
	Route("POST", "/admin/unnuke_user", admin(3), False),
	Route("POST", "/admin/unverify/<id>", admin(3), False),
	Route("POST", "/admin/update_filter_status", admin(2), False),
	Route("GET", "/admin/users", admin(2), False),
	Route("POST", "/admin/verify/<id>", admin(3), False),
	Route("GET", "/admins", ANYONE, True),
	Route("POST", "/allow_nsfw", PUBLIC, True),
	Route("GET", "/api", ANYONE, True),
	Route("POST", "/api_keys", USER, False),
	Route("GET", "/assets/<path>", PUBLIC, True),
	Route("GET", "/authorize", USER, False),
	Route("POST", "/authorize", USER, False),
	Route("POST", "/ban_user/<id>", admin(2), False),
	Route("GET", "/banned", ANYONE, True),
	Route("GET", "/blocks", admin(2), False),
	Route("GET", "/catalog", ANYONE, True),
	Route("GET", "/changelog", USER, True),
	Route("POST", "/changelogsub", USER, True),
	Route("GET", "/chart", PUBLIC, True),
	Route("POST", "/clear", USER, True),
	Route("POST", "/comment", USER, True),
	Route("GET", "/comment/<id>", ANYONE, True),
	Route("GET", "/comments", USER, True),
	Route("GET", "/contact", ANYONE, True),
	Route("GET", "/daily_chart", admin(2), False),
	Route("POST", "/delete/comment/<id>", USER, True),
	Route("POST", "/delete_app/<id>", USER, False),
	Route("POST", "/delete_post/<id>", USER, True),
	Route("POST", "/dismiss_mobile_tip", PUBLIC, True),
	Route("POST", "/distinguish/<id>", admin(1), False),
	Route("POST", "/distinguish_comment/<id>", admin(1), False),
	Route("POST", "/edit_app/<id>", USER, False),
	Route("POST", "/edit_comment/<id>", USER, True),
	Route("POST", "/edit_post/<id>", USER, True),
	Route("GET", "/feed", PUBLIC, True),
	Route("POST", "/filter_automatic/<id>", admin(2), False),
	Route("POST", "/filter_filtered/<id>", admin(2), False),
	Route("POST", "/filter_unfiltered/<id>", admin(2), False),
	Route("POST", "/follow/<text>", USER, True),
	Route("GET", "/forgot", PUBLIC, True),
	Route("POST", "/forgot", PUBLIC, True),
	Route("GET", "/formatting", ANYONE, True),
	Route("GET", "/hostedimages/<text>", PUBLIC, True),
	Route("GET", "/id/<id>", PUBLIC, True),
	Route("POST", "/id/<id>/private/<text>", USER, True),
	Route("GET", "/images/<text>", PUBLIC, True),
	Route("GET", "/is_available/<text>", PUBLIC, True),
	Route("POST", "/is_repost", PUBLIC, True),
	Route("GET", "/leaderboard", admin(2), False),
	Route("GET", "/log", ANYONE, True),
	Route("GET", "/log/<id>", ANYONE, True),
	Route("GET", "/login", ANYONE, True),
	Route("POST", "/login", PUBLIC, True),
	Route("GET", "/logout", USER, True),
	Route("GET", "/lost_2fa", ANYONE, True),
	Route("GET", "/me", USER, True),
	Route("GET", "/media", ANYONE, True),
	Route("GET", "/modlog", ANYONE, True),
	Route("GET", "/morecomments/<id>", ANYONE, True),
	Route("GET", "/notifications", USER, True),
	Route("GET", "/notifications/messages", USER, True),
	Route("GET", "/notifications/modmail", admin(2), False),
	Route("GET", "/notifications/posts", USER, True),
	Route("POST", "/oauth/reroll/<id>", USER, False),
	Route("POST", "/oauth/rescind/<id>", USER, False),
	Route("POST", "/pin/<id>", USER, True),
	Route("GET", "/post/<id>", ANYONE, True),
	Route("GET", "/post/<id>/<text>", ANYONE, True),
	Route("GET", "/post/<id>/<text>/<id>", ANYONE, True),
	Route("GET", "/pp/<id>", PUBLIC, True),
	Route("GET", "/press", ANYONE, True),
	Route("POST", "/publish/<id>", USER, True),
	Route("GET", "/random_post", PUBLIC, True),
	Route("GET", "/random_user", PUBLIC, True),
	Route("POST", "/remove_follow/<text>", USER, True),
	Route("POST", "/reply", USER, True),
	Route("POST", "/report/comment/<id>", USER, True),
	Route("POST", "/report/post/<id>", USER, True),
	Route("POST", "/request_2fa_disable", PUBLIC, True),
	Route("GET", "/reset", PUBLIC, True),
	Route("POST", "/reset", ANYONE, True),
	Route("GET", "/reset_2fa", PUBLIC, True),
	Route("POST", "/reset_2fa", PUBLIC, True),
	Route("GET", "/robots.txt", PUBLIC, True),
	Route("GET", "/rss", PUBLIC, True),
	Route("GET", "/rss/<text>/<text>", PUBLIC, True),
	Route("GET", "/rules", ANYONE, True),
	Route("POST", "/save_comment/<id>", USER, True),
	Route("POST", "/save_post/<id>", USER, True),
	Route("GET", "/search/comments", USER, True),
	Route("GET", "/search/posts", USER, True),
	Route("GET", "/search/users", USER, True),
	Route("POST", "/send_admin", ANYONE, True),
	Route("GET", "/settings", USER, True),
	Route("GET", "/settings/apps", USER, False),
	Route("POST", "/settings/block", USER, True),
	Route("GET", "/settings/blocks", USER, True),
	Route("GET", "/settings/content", USER, True),
	Route("GET", "/settings/css", USER, True),
	Route("POST", "/settings/css", USER, True),
	Route("POST", "/settings/filters", USER, True),
	Route("POST", "/settings/images/banner", USER, True),
	Route("POST", "/settings/images/profile", USER, True),
	Route("POST", "/settings/log_out_all_others", USER, True),
	Route("POST", "/settings/name_change", USER_NOT_PERMABANNED, True),
	Route("POST", "/settings/namecolor", USER, True),
	Route("GET", "/settings/profile", USER, True),
	Route("POST", "/settings/profile", USER, True),
	Route("GET", "/settings/profilecss", USER, True),
	Route("POST", "/settings/profilecss", USER, True),
	Route("GET", "/settings/security", USER, True),
	Route("POST", "/settings/security", USER, True),
	Route("POST", "/settings/themecolor", USER, True),
	Route("POST", "/settings/title_change", USER, True),
	Route("POST", "/settings/titlecolor", USER, True),
	Route("POST", "/settings/unblock", USER, True),
	Route("POST", "/settings/verifiedcolor", USER, True),
	Route("POST", "/shadowban/<id>", admin(2), False),
	Route("GET", "/sidebar", ANYONE, True),
	Route("GET", "/signup", ANYONE, True),
	Route("POST", "/signup", ANYONE, True),
	Route("GET", "/static/assets/<path>", PUBLIC, True),
	Route("GET", "/static/images/<text>", PUBLIC, True),
	Route("GET", "/stats", admin(2), False),
	Route("POST", "/sticky/<id>", admin(2), False),
	Route("POST", "/sticky_comment/<id>", admin(2), False),
	Route("GET", "/submit", USER, True),
	Route("POST", "/submit", USER, True),
	Route("GET", "/submit/title", USER, True),
	Route("POST", "/subscribe/<id>", USER, True),
	Route("GET", "/support", ANYONE, True),
	Route("GET", "/tasks", admin(2), False),
	Route("GET", "/tasks/<id>", admin(2), False),
	Route("GET", "/tasks/<id>/runs", admin(2), False),
	Route("GET", "/tasks/<id>/runs/<id>", admin(2), False),
	Route("POST", "/tasks/<id>/schedule", admin(2), False),
	Route("GET", "/tasks/scheduled_posts", admin(2), False),
	Route("POST", "/tasks/scheduled_posts", admin(2), False),
	Route("GET", "/tasks/scheduled_posts/<id>", admin(2), False),
	Route("POST", "/tasks/scheduled_posts/<id>/content", admin(2), False),
	Route("POST", "/tasks/scheduled_posts/<id>/schedule", admin(2), False),
	Route("POST", "/toggle_comment_nsfw/<id>", USER, True),
	Route("POST", "/toggle_post_nsfw/<id>", USER, True),
	Route("GET", "/u/<text>", PUBLIC, True),
	Route("GET", "/uid/<id>/pic", PUBLIC, True),
	Route("GET", "/uid/<id>/pic/profile", PUBLIC, True),
	Route("POST", "/unban_user/<id>", admin(2), False),
	Route("POST", "/undelete/comment/<id>", USER, True),
	Route("POST", "/undelete_post/<id>", USER, True),
	Route("POST", "/unfollow/<text>", USER, True),
	Route("GET", "/unread", USER, True),
	Route("POST", "/unsave_comment/<id>", USER, True),
	Route("POST", "/unsave_post/<id>", USER, True),
	Route("POST", "/unshadowban/<id>", admin(2), False),
	Route("POST", "/unsticky/<id>", admin(2), False),
	Route("POST", "/unsticky_comment/<id>", admin(2), False),
	Route("POST", "/unsubscribe/<id>", USER, True),
	Route("POST", "/verify_email", USER, True),
	Route("GET", "/viewmore/<id>/<text>/<text>", ANYONE, True),
	Route("GET", "/volunteer", USER, False),
	Route("POST", "/volunteer/submit", USER, False),
	Route("POST", "/vote/comment/<id>/<text>", USER_NOT_PERMABANNED, False),
	Route("POST", "/vote/post/<id>/<text>", USER_NOT_PERMABANNED, False),
	Route("GET", "/votes", admin(3), False),
	Route("GET", "/weekly_chart", admin(2), False),
]
