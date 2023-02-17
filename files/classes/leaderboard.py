from typing import Any, Callable, Optional, Union

from sqlalchemy import Column, func
from sqlalchemy.orm import scoped_session, Query

from files.helpers.const import LEADERBOARD_LIMIT

from files.classes.badges import Badge
from files.classes.marsey import Marsey
from files.classes.user import User
from files.classes.userblock import UserBlock

_LeaderboardValue = Union[int, Column]
_LeaderboardProperty = Optional[Union[Column, property]]
_LeaderboardReturn = tuple[list[User], Optional[int], Optional[int]]
_LeaderboardCallable = Callable[[_LeaderboardProperty, User, scoped_session, Optional[Query], int], _LeaderboardReturn]

class Leaderboard:
	"""
	Represents an request-context leaderboard. None of this is persisted yet,
	although this is probably a good idea to do at some point.
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
			self.value_func = lambda u:getattr(u, criteria.fget.__name__) or 0 # absolutely horrifying
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
