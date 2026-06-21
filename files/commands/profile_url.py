"""
Dev-only profiling harness for diagnosing slow render paths.

Renders a URL through the Flask test client and reports:
  * wall-clock time (without the profiler attached, so it's accurate)
  * SQL query count and total time in SQL (via the same g.query_count/
    g.query_time counters the [slow-request] logger uses)
  * a cProfile breakdown of the top frames by cumulative / total time

The request is anonymous by default (v=None), which matches the crawler
traffic that drives the post/comment render load.

Usage (inside the site container, against a loaded DB):

  flask profile_url '/post/882/culture-war-roundup-for-the-week/189868'
  flask profile_url '/post/882/x/189868?context=8' --repeat 5 --sort tottime
  flask profile_url '/post/882' --top 50
"""

import cProfile
import pstats
import time

import click
from flask import g

from files.__main__ import app


@app.cli.command("profile_url")
@click.argument("url")
@click.option("--repeat", default=3, help="Timed (unprofiled) iterations.")
@click.option("--warmup", default=1, help="Warmup iterations (compile templates, prime caches).")
@click.option("--profiled", default=1, help="Iterations run under cProfile.")
@click.option("--top", default=35, help="Number of profile rows to print.")
@click.option("--sort", default="cumulative", type=click.Choice(["cumulative", "tottime"]),
	help="Sort key for the profile table.")
@click.option("--user-id", default=None, type=int,
	help="Render as this user id (logged-in). Default: anonymous, matching bot traffic.")
@click.option("--dump", default=None, type=str,
	help="Write the rendered HTML to this path (for before/after diffing).")
def profile_url(url, repeat, warmup, profiled, top, sort, user_id, dump):
	client = app.test_client()

	# Capture per-request SQL counters via an after_request hook. Registered
	# here rather than at module import so importing this command never mutates
	# the app's request handlers -- only running the command installs it.
	request_stats: list[dict] = []

	@app.after_request
	def _capture_profile_stats(resp):
		request_stats.append({
			"queries": getattr(g, "query_count", 0),
			"sql_time": getattr(g, "query_time", 0.0),
			"status": resp.status_code,
			"bytes": resp.calculate_content_length() or len(resp.get_data()),
		})
		# flask.g persists across test_client() calls in one process, so reset
		# the counters per request to avoid accumulation.
		g.query_count = 0
		g.query_time = 0.0
		return resp

	# Optional: render as a logged-in user by planting the session cookie.
	if user_id is not None:
		from files.classes.user import User
		from files.__main__ import db_session
		u = db_session().query(User).get(user_id)
		if not u:
			raise click.ClickException(f"user id {user_id} not found")
		with client.session_transaction() as sess:
			sess["lo_user"] = u.id
			sess["login_nonce"] = u.login_nonce
		click.echo(f"rendering as @{u.username} (id={u.id}, admin_level={u.admin_level})")
	else:
		click.echo("rendering as: anonymous (matches crawler traffic)")

	def hit():
		request_stats.clear()
		t0 = time.perf_counter()
		resp = client.get(url, headers={"User-Agent": "profile_url"})
		dt = time.perf_counter() - t0
		st = request_stats[-1] if request_stats else {}
		return resp, dt, st

	click.echo(f"\nURL: {url}\n")

	if dump:
		resp, _, _ = hit()
		with open(dump, "wb") as fh:
			fh.write(resp.get_data())
		click.echo(f"wrote {dump} ({len(resp.get_data())} bytes, status {resp.status_code})")
		return

	for i in range(warmup):
		resp, dt, st = hit()
		click.echo(f"[warmup {i}] {st.get('status')} {dt*1000:7.0f}ms  "
			f"{st.get('queries',0):4d} queries  {st.get('sql_time',0.0):.2f}s sql  "
			f"{st.get('bytes',0)//1024} KB")

	# Accurate timing pass (no profiler overhead).
	times, qs, sqls = [], [], []
	for i in range(repeat):
		resp, dt, st = hit()
		times.append(dt)
		qs.append(st.get("queries", 0))
		sqls.append(st.get("sql_time", 0.0))
		click.echo(f"[timed  {i}] {st.get('status')} {dt*1000:7.0f}ms  "
			f"{st.get('queries',0):4d} queries  {st.get('sql_time',0.0):.2f}s sql  "
			f"{st.get('bytes',0)//1024} KB")

	if times:
		wall = min(times)
		sql = min(sqls) if sqls else 0.0
		click.echo("")
		click.echo(f"  wall (min):    {wall*1000:.0f} ms")
		click.echo(f"  queries:       {qs[0] if qs else 0}")
		click.echo(f"  time in sql:   {sql*1000:.0f} ms  ({100*sql/wall:.1f}% of wall)")
		click.echo(f"  time in python:{(wall-sql)*1000:.0f} ms  ({100*(wall-sql)/wall:.1f}% of wall)")

	# Profiled pass.
	click.echo(f"\n===== cProfile (top {top} by {sort}), {profiled} iteration(s) =====")
	pr = cProfile.Profile()
	pr.enable()
	for _ in range(profiled):
		hit()
	pr.disable()
	stats = pstats.Stats(pr)
	stats.sort_stats(sort)
	stats.print_stats(top)
