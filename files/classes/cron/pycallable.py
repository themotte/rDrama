import importlib
from types import ModuleType
from typing import Callable

from sqlalchemy.schema import Column
from sqlalchemy.sql.sqltypes import String

from files.classes.cron.scheduler import RepeatableTask, TaskRunContext

_TABLE_NAME = "tasks_repeatable_python"


class PythonCodeTask(RepeatableTask):
	__tablename__ = _TABLE_NAME	
	
	__mapper_args__ = {
		"polymorphic_identity": _TABLE_NAME,
		"concrete": True,
	}

	import_path = Column(String, nullable=False)
	callable = Column(String, nullable=False)
	
	def run_task(self, ctx:TaskRunContext):
		self.get_function()(ctx)

	def get_function(self) -> Callable[[TaskRunContext], None]:
		module:ModuleType = importlib.import_module(self.import_path)
		fn = getattr(module, self.callable, None)
		if not callable(fn):
			raise TypeError("Name either does not exist or is not callable")
		return fn
