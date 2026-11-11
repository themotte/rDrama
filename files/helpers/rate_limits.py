'''
Rate limits: how many requests each client may have served in a window of time.

A route has its own limits (`limit`), the site's default ones, or none (`exempt`). A request a route serves counts toward the route's limits for its client, toward the client's site-wide limits unless the route is exempt, and, when its User-Agent is a crawler's, toward that User-Agent's crawler limits on the route. Each (method, path pattern) counts apart, HEAD as GET; OPTIONS and requests no route answers aren't counted.

A limit of N per period P serves N requests in each window [kP, (k+1)P) of the Unix epoch's seconds. A request is refused (429) when any of its limits has already served N in its window, and then counts toward none of them.
'''
import time
from typing import Callable, NamedTuple

import redis
from flask import abort, current_app, request

_PERIODS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}

# A counter outlives its window by this much on Redis's clock, so that a window still open on the limiter's clock doesn't expire on Redis's when that clock runs behind it, as a test's stopped clock does for the test's length
_COUNTER_GRACE = 60

# Serves a request when every counter (KEYS) is below its count (ARGV 1..n), and then counts it in all of them, each kept for its lifetime (ARGV n+1..2n)
_SERVE = """
for i, key in ipairs(KEYS) do
	if tonumber(redis.call('GET', key) or '0') >= tonumber(ARGV[i]) then
		return 0
	end
end
for i, key in ipairs(KEYS) do
	if redis.call('INCR', key) == 1 then
		redis.call('EXPIRE', key, ARGV[#KEYS + i])
	end
end
return 1
"""


class Limit(NamedTuple):
	count: int
	period: int


def parse(text: str) -> tuple[Limit, ...]:
	'''The limits of a text like "1/second;30/minute".'''
	limits = []
	for part in text.split(";"):
		count, _, unit = part.partition("/")
		limits.append(Limit(int(count), _PERIODS[unit]))
	return tuple(limits)


def client_address() -> str | None:
	'''The client a request comes from: the address in its X-Real-IP header, set by the proxy in front of the site, or, without one, the connection's peer.'''
	real_ip = (request.headers.get('X-Real-IP') or '').strip()
	return real_ip or request.remote_addr


class RateLimiter:
	def __init__(self, redis_url: str, *, default: str, site_wide: str, crawlers: str, is_crawler: Callable[[], bool], enabled: bool):
		self.enabled = enabled
		# What the windows are measured by, and the signup form's minimum filling time
		self.clock: Callable[[], float] = time.time
		self._default = parse(default)
		self._site_wide = parse(site_wide)
		self._crawlers = parse(crawlers)
		self._is_crawler = is_crawler
		self._serve = redis.Redis.from_url(redis_url).register_script(_SERVE)

	def limit(self, text: str):
		'''Gives the route this decorates its own limits in place of the default ones.'''
		limits = parse(text)
		def mark(view):
			view.rate_limits = limits
			return view
		return mark

	def exempt(self, view):
		'''Takes the route this decorates out of its own and the site-wide limits.'''
		view.rate_limits = ()
		return view

	def check(self):
		'''Refuses (429) a request over any of its limits, or counts it; a before_request handler.'''
		if not self.enabled or request.url_rule is None or request.method == "OPTIONS":
			return
		route = f"{'GET' if request.method == 'HEAD' else request.method} {request.url_rule.rule}"
		own = getattr(current_app.view_functions[request.endpoint], "rate_limits", None)
		client = client_address()
		counters = []
		if own != ():
			counters += [(f"{route}:{client}", limit) for limit in own or self._default]
			counters += [(f"site:{client}", limit) for limit in self._site_wide]
		if self._is_crawler():
			counters += [(f"crawler:{route}:{request.headers.get('User-Agent')}", limit) for limit in self._crawlers]
		self._count(counters)

	def check_now(self, scope: str, text: str):
		'''Refuses (429) the client's current request, or counts it, under `scope`'s limits `text`: for what isn't a route, such as a socket event.'''
		if self.enabled:
			self._count([(f"{scope}:{client_address()}", limit) for limit in parse(text)])

	def _count(self, counters: list[tuple[str, Limit]]):
		if not counters:
			return
		now = self.clock()
		keys = [f"ratelimit:{scope}:{limit.count}/{limit.period}:{int(now // limit.period)}" for scope, limit in counters]
		args = [limit.count for _, limit in counters] + [limit.period + _COUNTER_GRACE for _, limit in counters]
		if not self._serve(keys=keys, args=args):
			abort(429)
