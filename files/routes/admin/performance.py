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

PROCESS_NAME: Final[str] = "gunicorn"
'''
The name of the master and worker processes
'''

INIT_PID: Final[int] = 1
'''
The PID of the init process. Used to check an edge case for orphaned workers.
'''

MEMORY_RSS_WARN_LEVELS_MASTER: dict[int, str] = {
	0: '',
	50 * 1024 * 1024: 'text-warn',
	75 * 1024 * 1024: 'text-danger',
}
'''
Levels to warn for in RAM memory usage for the master process. The master 
process shouldn't be using much RAM at all since all it basically does is
orchestrate workers.
'''

MEMORY_RSS_WARN_LEVELS_WORKER: dict[int, str] = {
	0: '',
	200 * 1024 * 1024: 'text-warn',
	300 * 1024 * 1024: 'text-danger',
}
'''
Levels to warn for in RAM memory usage. There are no warning levels for VM 
usage because Python seems to intentionally overallocate (presumably to make 
the interpreter faster) and doesn't tend to touch many of its owned pages.
'''

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
		levels: dict[int, str] = MEMORY_RSS_WARN_LEVELS_MASTER \
			if self.is_master else MEMORY_RSS_WARN_LEVELS_WORKER
		for mem, css in levels.items():
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
	processes = {p.pid:RenderedPerfInfo.from_process(p) 
	      for p in psutil.process_iter() 
		  if p.name() == PROCESS_NAME}
	return render_template('admin/performance/memory.html', v=v, processes=processes, system_vm=system_vm)

def _signal_master_process(signal:int) -> None:
	ppid:int = os.getppid()
	if ppid == INIT_PID: # shouldn't happen but handle the orphaned worker case just in case
		abort(500, "This worker is an orphan!")
	os.kill(ppid, signal)

def _signal_worker_process(pid:int, signal:int) -> None:
	workers:set[int] = {p.pid 
		     for p in psutil.process_iter() 
			 if p.name() == PROCESS_NAME}
	workers.discard(os.getppid()) # don't allow killing the master process

	if not pid in workers:
		abort(404, "Worker process not found")
	os.kill(pid, signal)

@app.post('/performance/workers/reload')
@admin_level_required(PERMS['PERFORMANCE_RELOAD'])
def performance_reload_workers(v):
	_signal_master_process(Signals.SIGHUP)
	return {'message': 'Sent reload signal successfully'}

@app.post('/performance/workers/<int:pid>/terminate')
@admin_level_required(PERMS['PERFORMANCE_KILL_PROCESS'])
def performance_terminate_worker_process(v, pid:int):
	_signal_worker_process(pid, Signals.SIGTERM)
	return {"message": f"Gracefully shut down worker PID {pid} successfully"}

@app.post('/performance/workers/<int:pid>/kill')
@admin_level_required(PERMS['PERFORMANCE_KILL_PROCESS'])
def performance_kill_worker_process(v, pid:int):
	_signal_worker_process(pid, Signals.SIGKILL)
	return {"message": f"Killed worker with PID {pid} successfully"}

@app.post('/performance/workers/+1')
@app.post('/performance/workers/-1')
@admin_level_required(PERMS['PERFORMANCE_SCALE_UP_DOWN'])
def performance_scale_up_down(v):
	scale_up:bool = '+1' in request.url
	_signal_master_process(Signals.SIGTTIN if scale_up else Signals.SIGTTOU)
	return {"message": "Sent signal to master to scale " + ("up" if scale_up else "down")}
