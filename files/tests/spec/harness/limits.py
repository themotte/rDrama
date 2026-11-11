'''
The site's rate limits: how many requests each client may have served in a window of time. This is specification content, kept in the harness so the spec's limit cells and the check that keeps the table equal to the site can share it.

Which limits a request counts toward:
- its route's (a row of routes.ROUTES): those OWN gives it, or DEFAULT, or none when it is EXEMPT. Each row counts apart, for each client: the GET and POST rows of a path, and two rows that look alike;
- the client's SITE_WIDE limits, across every row that isn't EXEMPT;
- when its User-Agent is a crawler's (is_crawler), the CRAWLERS limits of that User-Agent on its row, whatever the client, EXEMPT rows included.
HEAD counts toward its GET row, and OPTIONS toward nothing, nor does a request no row answers (404, 405, the redirect merging doubled slashes). Limits are counted after the checks every request gets and before the route's gate (routes.py), so a request its gate refuses counts like any other.

The client is the address in the request's X-Real-IP header, stripped of spaces, when it has one that isn't blank, and otherwise the peer the connection comes from. A deployment therefore puts the site behind a proxy that sets X-Real-IP, replacing any the client sent; without one, clients choose their own address.

A limit "N/period" serves N requests in each window of the period, the windows being aligned to the Unix epoch: a second is [k, k+1) in epoch seconds, a minute [60k, 60k+60), an hour [3600k, 3600k+3600), a day each UTC day. A request is refused with 429 (the error page, or JSON for scripts and API clients, as for any error) when any of its limits has already served N in its current window; a refused request counts toward none of them, and a served one toward all.

The spec runs with the limits off, but for its tests in the "limits" profile (config.PROFILES), where they are measured by a clock the test sets (harness.limit_clock_set). Those check each row's shortest limit, and every distinct limit up to 250 a window; the larger ones, such as the 1000 a day most rows allow, are held to this table only by the implementation's own check.

Several instances serving one site may each count apart, so a client may get more than a limit allows across them.
'''
from files.tests.spec.harness.routes import Route

DEFAULT = "3/second;30/minute;200/hour;1000/day"
SITE_WIDE = "10/second;200/minute;5000/hour;10000/day"
CRAWLERS = "12/minute"

_CRAWLER_WORDS = ("bot", "bytespider", "chatgpt-user")


def is_crawler(user_agent: str) -> bool:
	'''Whether a User-Agent is a crawler's: one with any of these words in it, in any case.'''
	return any(word in user_agent.lower() for word in _CRAWLER_WORDS)


# Rows with limits of their own, sorted like ROUTES
OWN = {
	("GET", "/"): "3/second;30/minute;1000/hour;5000/day",
	("POST", "/@<text>/message"): "1/second;10/minute;20/hour;50/day",
	("POST", "/admin/app/approve/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/admin/app/reject/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/admin/app/revoke/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/api_keys"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/authorize"): "1/second;30/minute;200/hour;1000/day",
	("GET", "/catalog"): "3/second;30/minute;1000/hour;5000/day",
	("POST", "/comment"): "1/second;20/minute;200/hour;1000/day",
	("POST", "/delete/comment/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/delete_app/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/delete_post/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/edit_app/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/edit_comment/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/edit_post/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/follow/<text>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/forgot"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/login"): "1/second;6/minute;200/hour;1000/day",
	("GET", "/logout"): "1/second;30/minute;200/hour;1000/day",
	("GET", "/morecomments/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/oauth/reroll/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/oauth/rescind/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/publish/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/remove_follow/<text>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/reply"): "1/second;6/minute;50/hour;200/day",
	("POST", "/report/comment/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/report/post/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/request_2fa_disable"): "1/second;6/minute;200/hour;1000/day",
	("POST", "/reset"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/reset_2fa"): "1/second;6/minute;200/hour;1000/day",
	("POST", "/save_comment/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/save_post/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/send_admin"): "1/second;2/minute;6/hour;10/day",
	("POST", "/settings/block"): "1/second;10/day",
	("POST", "/settings/css"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/settings/images/banner"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/settings/images/profile"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/settings/log_out_all_others"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/settings/name_change"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/settings/namecolor"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/settings/profile"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/settings/profilecss"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/settings/security"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/settings/themecolor"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/settings/title_change"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/settings/titlecolor"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/settings/unblock"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/settings/verifiedcolor"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/signup"): "10/day",
	("POST", "/submit"): "1/second;2/minute;10/hour;50/day",
	("GET", "/submit/title"): "6/minute",
	("POST", "/subscribe/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/undelete/comment/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/undelete_post/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/unfollow/<text>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/unsave_comment/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/unsave_post/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/unsubscribe/<id>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/verify_email"): "1/second;30/minute;200/hour;1000/day",
	("GET", "/viewmore/<id>/<text>/<text>"): "1/second;30/minute;200/hour;1000/day",
	("POST", "/vote/comment/<id>/<text>"): "5/second;60/minute;600/hour;1000/day",
	("POST", "/vote/post/<id>/<text>"): "5/second;60/minute;600/hour;1000/day",
}

# Rows with no limits of their own, and outside the site-wide ones
EXEMPT = {
	("POST", "/@<text>/create_note"),
	("POST", "/@<text>/delete_note/<id>"),
	("POST", "/@<text>/make_admin"),
	("GET", "/@<text>/pic"),
	("POST", "/@<text>/remove_admin"),
	("POST", "/@<text>/revert_actions"),
	("GET", "/admin"),
	("GET", "/admin/alt_votes"),
	("GET", "/admin/banned_domains"),
	("POST", "/admin/banned_domains"),
	("POST", "/admin/dump_cache"),
	("GET", "/admin/filtered/comments"),
	("GET", "/admin/filtered/posts"),
	("GET", "/admin/image_posts"),
	("POST", "/admin/link_accounts"),
	("POST", "/admin/nuke_user"),
	("GET", "/admin/removed/comments"),
	("GET", "/admin/removed/posts"),
	("GET", "/admin/reported/comments"),
	("GET", "/admin/reported/posts"),
	("GET", "/admin/shadowbanned"),
	("POST", "/admin/site_settings/<text>"),
	("POST", "/admin/title_change/<id>"),
	("POST", "/admin/unnuke_user"),
	("POST", "/admin/unverify/<id>"),
	("POST", "/admin/update_filter_status"),
	("GET", "/admin/users"),
	("POST", "/admin/verify/<id>"),
	("GET", "/assets/<path>"),
	("POST", "/ban_user/<id>"),
	("POST", "/distinguish/<id>"),
	("POST", "/distinguish_comment/<id>"),
	("POST", "/filter_automatic/<id>"),
	("POST", "/filter_filtered/<id>"),
	("POST", "/filter_unfiltered/<id>"),
	("GET", "/hostedimages/<text>"),
	("GET", "/images/<text>"),
	("GET", "/pp/<id>"),
	("POST", "/shadowban/<id>"),
	("GET", "/static/assets/<path>"),
	("GET", "/static/images/<text>"),
	("POST", "/sticky/<id>"),
	("POST", "/sticky_comment/<id>"),
	("GET", "/uid/<id>/pic"),
	("GET", "/uid/<id>/pic/profile"),
	("POST", "/unban_user/<id>"),
	("POST", "/unshadowban/<id>"),
	("POST", "/unsticky/<id>"),
	("POST", "/unsticky_comment/<id>"),
	("GET", "/votes"),
}


_PERIODS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


def limits_of(route: Route) -> list[tuple[int, int]]:
	'''The (count, period in seconds) limits of a row's own, shortest period first; none when it is exempt.'''
	if (route.method, route.path) in EXEMPT:
		return []
	return parse(OWN.get((route.method, route.path), DEFAULT))


def parse(text: str) -> list[tuple[int, int]]:
	'''The (count, period in seconds) limits of a text like "1/second;30/minute".'''
	limits = []
	for part in text.split(";"):
		count, _, unit = part.partition("/")
		limits.append((int(count), _PERIODS[unit]))
	return sorted(limits, key=lambda limit: limit[1])
