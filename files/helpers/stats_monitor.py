"""
Periodic resource diagnostics for the gunicorn fleet.

Two small daemon threads, wired from ``gunicorn_config.py``:

* :func:`start_master_monitor` runs in the gunicorn *master* and logs one
  ``[stats] sys`` line every minute with system memory, swap, CPU, load
  average and aggregate worker RSS. Because it runs in the master it keeps
  emitting even while workers are timing out and being recycled, and it gives
  the otherwise timestamp-less ``[perf]`` / ``[slow-request]`` lines a
  per-minute anchor.

* :func:`start_worker_monitor` runs in each *worker* and logs one
  ``[stats] worker`` line every minute with that worker's RSS, CPU, open DB
  connections and in-flight request concurrency (current + peak over the
  minute). In-flight concurrency vs. the gthread pool size is the key signal
  for thread-pool / GIL saturation.

Both loops swallow their own exceptions so a monitoring hiccup can never take
down the master or a worker.
"""

import os
import sys
import threading
import time

import psutil

EMIT_INTERVAL = 60.0    # seconds between [stats] lines
SAMPLE_INTERVAL = 5.0   # how often the worker samples in-flight depth for its peak


def _mb(n_bytes):
	return n_bytes / (1024 * 1024)


def _utc():
	# Wall-clock UTC, matching the gunicorn access/error log timestamps.
	return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _emit(line):
	print(line, file=sys.stderr, flush=True)


def _master_loop():
	master = psutil.Process()
	psutil.cpu_percent(interval=None)  # prime; the first reading is meaningless
	while True:
		# Align to the top of the minute so the master line and all worker
		# lines cluster into one readable per-minute snapshot.
		time.sleep(max(1.0, EMIT_INTERVAL - (time.time() % EMIT_INTERVAL)))
		try:
			vm = psutil.virtual_memory()
			sw = psutil.swap_memory()
			cpu = psutil.cpu_percent(interval=None)
			try:
				load = "%.1f,%.1f,%.1f" % os.getloadavg()
			except (OSError, AttributeError):
				load = "n/a"  # not available on this platform
			rss_total = 0
			rss_max = 0
			workers = master.children(recursive=False)
			for w in workers:
				try:
					rss = w.memory_info().rss
				except psutil.Error:
					continue  # worker died mid-iteration
				rss_total += rss
				if rss > rss_max:
					rss_max = rss
			_emit(
				f"[stats] sys {_utc()} "
				f"mem={vm.percent:.0f}% avail={_mb(vm.available):.0f}MB "
				f"swap={sw.percent:.0f}%({_mb(sw.used):.0f}MB) "
				f"cpu={cpu:.0f}% load={load} "
				f"workers={len(workers)} "
				f"worker_rss={_mb(rss_total):.0f}MB(max {_mb(rss_max):.0f}MB)"
			)
		except Exception as e:
			_emit(f"[stats] sys error: {e}")


def _db_conns():
	"""Connections currently checked out of this worker's SQLAlchemy pool, or
	-1 if the pool doesn't expose the stat (e.g. NullPool)."""
	try:
		from files.__main__ import engine
		return engine.pool.checkedout()
	except Exception:
		return -1


def _worker_loop(thread_pool_size):
	try:
		from files.__main__ import active_requests
	except Exception as e:
		_emit(f"[stats] worker import error: {e}")
		return
	proc = psutil.Process()
	proc.cpu_percent(interval=None)  # prime
	pool = f"/{thread_pool_size}" if thread_pool_size else ""
	peak = 0
	last_minute = int(time.time() // EMIT_INTERVAL)
	while True:
		# Sample often so `peak` reflects bursts between emissions, but only
		# emit once per wall-clock minute (aligning with the master line).
		time.sleep(SAMPLE_INTERVAL)
		try:
			depth = len(active_requests)
			if depth > peak:
				peak = depth
			minute = int(time.time() // EMIT_INTERVAL)
			if minute != last_minute:
				_emit(
					f"[stats] worker {_utc()} pid={proc.pid} "
					f"rss={_mb(proc.memory_info().rss):.0f}MB "
					f"cpu={proc.cpu_percent(interval=None):.0f}% "
					f"db_conns={_db_conns()} "
					f"inflight={depth}{pool} peak={peak}{pool}"
				)
				peak = depth
				last_minute = minute
		except Exception as e:
			_emit(f"[stats] worker error: {e}")
			last_minute = int(time.time() // EMIT_INTERVAL)


def start_master_monitor():
	"""Start the master-side system stats thread. Call once, from the gunicorn
	``when_ready`` hook (which runs in the master/arbiter)."""
	threading.Thread(target=_master_loop, name="stats-master", daemon=True).start()


def start_worker_monitor(thread_pool_size=0):
	"""Start the per-worker stats thread. Call once per worker, from the
	gunicorn ``post_worker_init`` hook."""
	threading.Thread(target=_worker_loop, args=(thread_pool_size,),
	                 name="stats-worker", daemon=True).start()
