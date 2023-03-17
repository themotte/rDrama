from dataclasses import dataclass
from typing import Any, Callable, Final, Optional

from sqlalchemy import Column, func
from sqlalchemy.orm import scoped_session, Query

from files.helpers.config.const import LEADERBOARD_LIMIT

from files.classes.badges import Badge
from files.classes.marsey import Marsey
from files.classes.user import User
from files.classes.userblock import UserBlock
from files.helpers.get import get_accounts_dict

@dataclass(frozen=True, slots=True)
class LeaderboardMeta:
	header_name:str
	table_header_name:str
	html_id:str
	table_column_name:str
	user_relative_url:Optional[str]
	limit:int=LEADERBOARD_LIMIT

class Leaderboard:
	def __init__(self, v:Optional[User], meta:LeaderboardMeta) -> None:
		self.v:Optional[User] = v
		self.meta:LeaderboardMeta = meta

	@property
	def all_users(self) -> list[User]:
		raise NotImplementedError()
	
	@property
	def v_position(self) -> Optional[int]:
		raise NotImplementedError()
	
	@property
	def v_value(self) -> Optional[int]:
		raise NotImplementedError()
	
	@property
	def v_appears_in_ranking(self) -> bool:
		return self.v_position is not None and self.v_position <= len(self.all_users)
	
	@property
	def user_func(self) -> Callable[[Any], User]:
		return lambda u:u
	
	@property
	def value_func(self) -> Callable[[User], int]:
		raise NotImplementedError()

class SimpleLeaderboard(Leaderboard):
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
	def value_func(self) -> Callable[[User], int]:
		return lambda u:getattr(u, self.column.name)
	
class _CountedAndRankedLeaderboard(Leaderboard):
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
		self._all_users = {k:v for k, v in leaderboard}
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

class RawSqlLeaderboard(Leaderboard):
	def __init__(self, meta:LeaderboardMeta, db:scoped_session, query:str) -> None: # should be LiteralString on py3.11+
		super().__init__(None, meta)
		self.db = db
		self._calculate(query)

	def _calculate(self, query:str):
		self.result = {result[0]:list(result) for result in self.db.execute(query).all()}
		users = get_accounts_dict(self.result.keys(), db=self.db)
		if users is None:
			raise Exception("Some users don't exist when they should (was a user deleted?)")
		for user in users: # I know.
			self.result[user].append(users[user])

	@property
	def all_users(self) -> list[User]:
		return [result[2] for result in self.result.values()]

	@property
	def v_position(self) -> Optional[int]:
		return None
	
	@property
	def v_value(self) -> Optional[int]:
		return None
	
	@property
	def v_appears_in_ranking(self) -> bool:
		return True # we set this to True here to try and not grab the data
	
	@property
	def user_func(self) -> Callable[[Any], User]:
		return lambda u:u
	
	@property
	def value_func(self) -> Callable[[User], int]:
		return lambda u:self.result[u.id][1]

class ReceivedDownvotesLeaderboard(RawSqlLeaderboard):
	_query: Final[str] = """
	WITH cv_for_user AS (
    SELECT
        comments.author_id AS target_id,
        COUNT(*)
    FROM commentvotes cv
        JOIN comments ON comments.id = cv.comment_id
    WHERE vote_type = -1
    GROUP BY comments.author_id
), sv_for_user AS (
    SELECT
        submissions.author_id AS target_id,
        COUNT(*)
    FROM votes sv
        JOIN submissions ON submissions.id = sv.submission_id
    WHERE vote_type = -1
    GROUP BY submissions.author_id
)
SELECT 
    COALESCE(cvfu.target_id, svfu.target_id) AS target_id,
    (COALESCE(cvfu.count, 0) + COALESCE(svfu.count, 0)) AS count
FROM cv_for_user cvfu
    FULL OUTER JOIN sv_for_user svfu
    ON cvfu.target_id = svfu.target_id
ORDER BY count DESC LIMIT 25
	"""

	def __init__(self, meta:LeaderboardMeta, db:scoped_session) -> None:
		super().__init__(meta, db, self._query)

class GivenUpvotesLeaderboard(RawSqlLeaderboard):
	_query: Final[str] = """
	SELECT 
    COALESCE(cvbu.user_id, svbu.user_id) AS user_id,
    (COALESCE(cvbu.count, 0) + COALESCE(svbu.count, 0)) AS count
FROM (SELECT user_id, COUNT(*) FROM votes WHERE vote_type = 1 GROUP BY user_id) AS svbu
FULL OUTER JOIN (SELECT user_id, COUNT(*) FROM commentvotes WHERE vote_type = 1 GROUP BY user_id) AS cvbu
    ON cvbu.user_id = svbu.user_id
ORDER BY count DESC LIMIT 25
	"""

	def __init__(self, meta:LeaderboardMeta, db:scoped_session) -> None:
		super().__init__(meta, db, self._query)
