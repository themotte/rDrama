import importlib
from types import ModuleType
from typing import Callable

from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.sql.sqltypes import String, Integer

from files.classes.cron.scheduler import RepeatableTask, TaskRunContext

_TABLE_NAME = "tasks_repeatable_python"

__all__ = ('PythonCodeTask',)

class PythonCodeTask(RepeatableTask):
	'''
	A repeatable task that is naively calls a Python callable. It can access
	all of the app state as that is provided to the callee. An example task 
	that sets the fictional `hams` variable on a `User` to `eggs` is shown
	below.

	```py
	from files.classes.user import User
	from files.classes.cron.scheduler import TaskRunContext
	from files.helpers.get import get_account
	
	def spam_task(ctx:TaskRunContext):
		user:Optional[User] = get_account(1784, graceful=True, db=ctx.db)
		if not user: raise Exception("User not found!")
		user.hams = "eggs"
		ctx.db.commit()
	```

	The `import_path` and `callable` properties are passed to `importlib`
	which then imports the module and then calls the callable with the current
	task context.
	'''
	
	__tablename__ = _TABLE_NAME	
	
	__mapper_args__ = {
		"polymorphic_identity": _TABLE_NAME,
	}

	id = Column(Integer, ForeignKey(RepeatableTask.id), primary_key=True)
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
