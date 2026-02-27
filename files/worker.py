"""
Custom Gunicorn worker that processes queued requests in LIFO order.

Under load, Gunicorn's default FIFO thread pool processes the oldest
queued requests first. By the time those requests are served, clients
have often already timed out and retried -- so the server wastes work
on stale requests while fresh ones queue up behind them. This creates
a death spiral: retries double inbound load on an already saturated
server.

LIFO scheduling flips this: when a thread becomes free, it picks up
the *newest* queued request, which is most likely to still have a
client waiting. Old requests that get starved out are ones whose
clients have already moved on.

Usage: gunicorn -k files.worker.LifoThreadWorker ...
"""

import queue
from concurrent.futures import ThreadPoolExecutor

from gunicorn.workers.gthread import ThreadWorker


class LifoThreadPoolExecutor(ThreadPoolExecutor):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._work_queue = queue.LifoQueue()


class LifoThreadWorker(ThreadWorker):
	def get_thread_pool(self):
		return LifoThreadPoolExecutor(max_workers=self.cfg.threads)
