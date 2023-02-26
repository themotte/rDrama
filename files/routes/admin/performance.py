import os
from dataclasses import dataclass
from signal import Signals
from typing import Final

import psutil
from flask import abort, render_template, request

from files.helpers.const import PERMS
from files.helpers.time import format_datetime
from files.helpers.wrappers import admin_level_required
from files.__main__ import app

WORKER_PROCESS_NAME: Final[str] = "gunicorn"
INIT_PID: Final[int] = 1

MEMORY_RSS_WARN_LEVELS_WORKER: dict[int, str] = {
	0: '',
	200 * 1024 * 1024: 'text-warn',
	300 * 1024 * 1024: 'text-danger',
}

@dataclass(frozen=True, slots=True)
class RenderedPerfInfo:
	pid:int
	started_at_utc:float
	memory_rss:int
	memory_vms:int

	@classmethod
	def from_process(cls, p:psutil.Process) -> "RenderedPerfInfo":
		with p.oneshot():
			mem = p.memory_info()
			return cls(pid=p.pid, started_at_utc=p.create_time(),
	                   memory_rss=mem.rss, memory_vms=mem.vms)
	
	@property
	def is_master(self) -> bool:
		return self.pid == os.getppid() and self.pid != INIT_PID

	@property
	def is_current(self) -> bool:
		return self.pid == os.getpid()
	
	@property
	def memory_rss_css_class(self) -> str:
		last = ''
		for mem, css in MEMORY_RSS_WARN_LEVELS_WORKER.items():
			if self.memory_rss < mem: return last
			last = css
		return last

	@property
	def started_at_utc_str(self) -> str:
		return format_datetime(self.started_at_utc)

@app.get('/performance/')
@admin_level_required(PERMS['PERFORMANCE_STATS'])
def performance_get_stats(v):
	system_vm = psutil.virtual_memory()
	processes = {p.pid:RenderedPerfInfo.from_process(p) for p in psutil.process_iter() if p.name() == WORKER_PROCESS_NAME}
	return render_template('admin/performance/memory.html', v=v, processes=processes, system_vm=system_vm)

def _signal_master_process(signal:int) -> None:
	ppid:int = os.getppid()
	if ppid == INIT_PID: # shouldn't happen but handle the orphaned worker case just in case
		abort(500, "This worker is an orphan!")
	os.kill(ppid, signal)

@app.post('/performance/workers/reload')
@admin_level_required(PERMS['PERFORMANCE_RELOAD'])
def performance_reload_workers(v):
	_signal_master_process(Signals.SIGHUP)
	return {'message': 'Sent reload signal successfully'}

@app.post('/performance/workers/<int:pid>/kill')
@admin_level_required(PERMS['PERFORMANCE_KILL_PROCESS'])
def performance_kill_worker_process(v, pid:int):
	workers:set[int] = {p.pid for p in psutil.process_iter() if p.name() == WORKER_PROCESS_NAME}
	try:
		workers.remove(os.getppid()) # don't allow killing the master process
	except:
		pass

	if not pid in workers:
		abort(404, "Worker process not found")
	os.kill(pid, Signals.SIGKILL)
	return {"message": f"Killed worker with PID {pid} successfully"}

@app.post('/performance/workers/+1')
@app.post('/performance/workers/-1')
@admin_level_required(PERMS['PERFORMANCE_SCALE_UP_DOWN'])
def performance_scale_up_down(v):
	scale_up:bool = '+1' in request.url
	signal:int = Signals.SIGTTIN if scale_up else Signals.SIGTTOU
	_signal_master_process(Signals.SIGTTIN if scale_up else Signals.SIGTTOU)
	return {"message": "Sent signal to master to scale " + ("up" if scale_up else "down")}
