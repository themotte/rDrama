from dataclasses import dataclass
from typing import Any, Callable, Optional, Union

from sqlalchemy import Column, func
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import scoped_session, Query

from files.helpers.const import LEADERBOARD_LIMIT

from files.classes.badges import Badge
from files.classes.marsey import Marsey
from files.classes.user import User
from files.classes.userblock import UserBlock

_LeaderboardValue = Union[int, Column]
_LeaderboardProperty = Optional[Union[property, Column]]
_LeaderboardReturn = tuple[list[User], Optional[int], Optional[int]]
_LeaderboardCallable = Callable[[_LeaderboardProperty, User, scoped_session, Optional[Query], int], _LeaderboardReturn]




@dataclass(frozen=True, slots=True)
class LeaderboardMeta:
	header_name:str
	table_header_name:str
	html_id:str
	table_column_name:str
	user_relative_url:Optional[str]
	limit:int=LEADERBOARD_LIMIT

class Leaderboard2:
	def __init__(self, v:User, meta:LeaderboardMeta) -> None:
		self.v:User = v
		self.meta:LeaderboardMeta = meta

	@property
	def all_users(self) -> list[User]:
		raise NotImplementedError()
	
	@property
	def v_position(self) -> Optional[int]:
		raise NotImplementedError()
	
	@property
	def v_value(self) -> int:
		raise NotImplementedError()
	
	@property
	def v_appears_in_ranking(self) -> bool:
		return self.v_position is not None and self.v_position <= len(self.all_users)
	
	@property
	def user_func(self) -> Callable[[Any], User]:
		raise NotImplementedError()
	
	@property
	def value_func(self) -> Callable[[User], int]:
		raise NotImplementedError()

class SimpleLeaderboard(Leaderboard2):
	def __init__(self, v:User, meta:LeaderboardMeta, db:scoped_session, users_query:Query, column:Column):
		super().__init__(v, meta)
		self.db:scoped_session = db
		self.users_query:Query = users_query
		self.column:Column = column
		self._calculate()

	def _calculate(self) -> None:
		self._all_users = self.users_query.order_by(self.column.desc()).limit(self.meta.limit).all()
		if self.v not in self._all_users:
			sq = self.db.query(User.id, self.column, func.rank().over(order_by=self.column.desc()).label("rank")).subquery()
			sq_data = self.db.query(sq.c.id, sq.c.column, sq.c.rank).filter(sq.c.id == self.v.id).limit(1).one()
			self._v_value:int = sq_data[1]
			self._v_position:int = sq_data[2]

	@property
	def all_users(self) -> list[User]:
		return self._all_users
	
	@property
	def v_position(self) -> int:
		return self._v_position
	
	@property
	def v_value(self) -> int:
		return self._v_value
	
	@property
	def user_func(self) -> Callable[[Any], User]:
		return lambda u:u
	
	@property
	def value_func(self) -> Callable[[User], int]:
		return lambda u:getattr(u, self.column.name)
	
class _CountedAndRankedLeaderboard(Leaderboard2):
	@classmethod
	def count_and_label(cls, criteria):
		return func.count(criteria).label("count")
	
	@classmethod
	def rank_filtered_rank_label_by_desc(cls, criteria):
		return func.rank().over(order_by=func.count(criteria).desc()).label("rank")
	
class BadgeMarseyLeaderboard(_CountedAndRankedLeaderboard):
	def __init__(self, v:User, meta:LeaderboardMeta, db:scoped_session, column:Column):
		super().__init__(v, meta)
		self.db:scoped_session = db
		self.column = column
		self._calculate()

	def _calculate(self):
		sq = self.db.query(self.column, self.count_and_label(self.column), self.rank_filtered_rank_label_by_desc(self.column)).group_by(self.column).subquery()
		sq_criteria = None
		if self.column == Badge.user_id:
			sq_criteria = User.id == sq.c.user_id
		elif self.column == Marsey.author_id:
			sq_criteria = User.id == sq.c.author_id
		else:
			raise ValueError("This leaderboard function only supports Badge.user_id and Marsey.author_id")
		leaderboard = self.db.query(User, sq.c.count).join(sq, sq_criteria).order_by(sq.c.count.desc())
		
		position:Optional[tuple[int, int, int]] = self.db.query(User.id, sq.c.rank, sq.c.count).join(sq, sq_criteria).filter(User.id == self.v.id).one_or_none()
		if position and position[1]:
			self._v_position = position[1]
			self._v_value = position[2]
		else:
			self._v_position = leaderboard.count() + 1
			self._v_value = 0
		self._all_users = {k:v for k, v in leaderboard.limit(self.meta.limit).all()}

	@property
	def all_users(self) -> list[User]:
		return list(self._all_users.keys())
	
	@property
	def v_position(self) -> int:
		return self._v_position
	
	@property
	def v_value(self) -> int:
		return self._v_value
	
	@property
	def value_func(self) -> Callable[[User], int]:
		return lambda u:self._all_users[u]
	
class UserBlockLeaderboard(_CountedAndRankedLeaderboard):
	def __init__(self, v:User, meta:LeaderboardMeta, db:scoped_session, column:Column):
		super().__init__(v, meta)
		self.db:scoped_session = db
		self.column = column
		self._calculate()
	
	def _calculate(self):
		if self.column != UserBlock.target_id:
			raise ValueError("This leaderboard function only supports UserBlock.target_id")
		sq = self.db.query(self.column, self.count_and_label(self.column)).group_by(self.column).subquery()
		leaderboard = self.db.query(User, sq.c.count).join(User, User.id == sq.c.target_id).order_by(sq.c.count.desc())
		
		sq = self.db.query(self.column, self.count_and_label(self.column), self.rank_filtered_rank_label_by_desc(self.column)).group_by(self.column).subquery()
		position = self.db.query(sq.c.rank, sq.c.count).join(User, User.id == sq.c.target_id).filter(sq.c.target_id == self.v.id).limit(1).one_or_none()
		if not position: position = (leaderboard.count() + 1, 0)
		leaderboard = leaderboard.limit(self.meta.limit).all()
		self._all_users = {k:v for k, v in leaderboard.limit(self.meta.limit).all()}
		self._v_position = position[0]
		self._v_value = position[1]
		return (leaderboard, position[0], position[1])

	@property
	def all_users(self) -> list[User]:
		return list(self._all_users.keys())
	
	@property
	def v_position(self) -> int:
		return self._v_position
	
	@property
	def v_value(self) -> int:
		return self._v_value


class _DeprecatedLeaderboard:
	"""
	Represents an request-context leaderboard. None of this is persisted yet,
	although this is probably a good idea to do at some point.

	Example 
	```
	truescore = Leaderboard("Truescore", "truescore", "truescore", "Truescore", None, Leaderboard.get_simple_lb, User.truecoins, v, lambda u:u.truecoins, g.db, users)
	```

	"""
	all_users:Optional[list[User]] = None
	v_position:Optional[int] = 0
	v_value:Optional[_LeaderboardValue] = None
	v_appears_in_ranking:bool = False
	user_func = None
	value_func = None

	# truescore = Leaderboard("Truescore", "truescore", "truescore", "Truescore", None, Leaderboard.get_simple_lb, User.truecoins, v, lambda u:u.truecoins, g.db, users)

	def __init__(self, header_name:str, table_header_name:str, html_id:str, 
	      		table_column_name:str, user_relative_url:Optional[str], 
				query_function:_LeaderboardCallable, criteria: _LeaderboardProperty, # Leaderboard.get_simple_lb, User.truecoins, v, lambda u:u.truecoins, g.db, users)
				v:User, value_func:Optional[Callable[[User], _LeaderboardValue]], 
				db:scoped_session, users:Optional[Query], limit=LEADERBOARD_LIMIT, **kwargs):
		self.header_name = header_name
		self.table_header_name = table_header_name
		self.html_id = html_id
		self.table_column_name = table_column_name
		self.user_relative_url = user_relative_url
		self.limit = limit

		lb = query_function(criteria, v, db, users, limit)
		self.all_users = lb[0]
		self.v_position = lb[1]
		self.v_value = lb[2]
		self.v_appears_in_ranking = bool(self.v_position and self.v_position <= len(self.all_users))
		if value_func:
			self.user_func = lambda u:u
			self.value_func = value_func
			self.v_value = value_func(v)
		elif criteria:
			self.user_func = lambda u:u
			if isinstance(criteria, property):
				self.value_func = lambda u:getattr(u, criteria.fget.__name__) or 0 # absolutely horrifying
			else:
				self.value_func = lambda u:getattr(u, criteria.name) or 0
		else:
			self.user_func = lambda u:u[0]
			self.value_func = lambda u: u[1] or 0

	@classmethod
	def get_simple_lb(cls, order_by, v:User, db:scoped_session, users:Optional[Query], limit:int):
		leaderboard = users.order_by(order_by.desc()).limit(limit).all()
		position:Optional[int] = None
		if v not in leaderboard:
			sq = db.query(User.id, func.rank().over(order_by=order_by.desc()).label("rank")).subquery()
			position = db.query(sq.c.id, sq.c.rank).filter(sq.c.id == v.id).limit(1).one()[1]
		return (leaderboard, position, None)
	
	@classmethod
	def count_and_label(cls, criteria):
		return func.count(criteria).label("count")
	
	@classmethod
	def rank_filtered_rank_label_by_desc(cls, criteria):
		return func.rank().over(order_by=func.count(criteria).desc()).label("rank")

	@classmethod
	def get_badge_marsey_lb(cls, lb_criteria, v:User, db:scoped_session, users:Optional[Query], limit):
		sq = db.query(lb_criteria, cls.count_and_label(lb_criteria), cls.rank_filtered_rank_label_by_desc(lb_criteria)).group_by(lb_criteria).subquery()
		sq_criteria = None
		if lb_criteria == Badge.user_id:
			sq_criteria = User.id == sq.c.user_id
		elif lb_criteria == Marsey.author_id:
			sq_criteria = User.id == sq.c.author_id
		else:
			raise ValueError("This leaderboard function only supports Badge.user_id and Marsey.author_id")
		
		leaderboard = db.query(User, sq.c.count).join(sq, sq_criteria).order_by(sq.c.count.desc())
		position = db.query(User.id, sq.c.rank, sq.c.count).join(sq, sq_criteria).filter(User.id == v.id).one_or_none()
		if position: position = (position[1], position[2])
		else: position = (leaderboard.count() + 1, 0)
		leaderboard = leaderboard.limit(limit).all()
		return (leaderboard, position[0], position[1])
	
	@classmethod
	def get_blockers_lb(cls, lb_criteria, v:User, db:scoped_session, users:Optional[Query], limit):
		if lb_criteria != UserBlock.target_id:
			raise ValueError("This leaderboard function only supports UserBlock.target_id")
		sq = db.query(lb_criteria, cls.count_and_label(lb_criteria)).group_by(lb_criteria).subquery()
		leaderboard = db.query(User, sq.c.count).join(User, User.id == sq.c.target_id).order_by(sq.c.count.desc())
		
		sq = db.query(lb_criteria, cls.count_and_label(lb_criteria), cls.rank_filtered_rank_label_by_desc(lb_criteria)).group_by(lb_criteria).subquery()
		position = db.query(sq.c.rank, sq.c.count).join(User, User.id == sq.c.target_id).filter(sq.c.target_id == v.id).limit(1).one_or_none()
		if not position: position = (leaderboard.count() + 1, 0)
		leaderboard = leaderboard.limit(limit).all()
		return (leaderboard, position[0], position[1])
