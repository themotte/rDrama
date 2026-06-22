import logging

from sqlalchemy.orm import Session

from files.__main__ import app, cache, db_session
from files.classes.cron.tasks import TaskRunContext
from files.classes.leaderboard import (GivenUpvotesLeaderboard,
                                        ReceivedDownvotesLeaderboard)

# The expensive raw-SQL leaderboards, refreshed together by this job.
_RAW_SQL_LEADERBOARDS = (ReceivedDownvotesLeaderboard, GivenUpvotesLeaderboard)


def leaderboard_recalc(db: Session, cache) -> None:
	'''
	Recomputes the expensive raw-SQL leaderboards (most downvotes received, most
	upvotes given) and stores their rows in the cache for request handlers to
	read.

	These aggregations scan the full votes/commentvotes tables. They used to run
	on every gunicorn worker boot (in ``files.helpers.services``), which under
	worker churn turned into a storm of full-table aggregations and helped drive
	CPU-saturation spirals. They now run once a day via cron instead.
	'''
	for lb_cls in _RAW_SQL_LEADERBOARDS:
		logging.info(f"Recalculating leaderboard: {lb_cls.__name__}")
		lb_cls.refresh_cache(db, cache)
	logging.info("Finished recalculating cached leaderboards")


def leaderboard_recalc_cron(ctx: TaskRunContext) -> None:
	leaderboard_recalc(ctx.db, ctx.cache)


@app.cli.command('leaderboard_recalc')
def leaderboard_recalc_cmd():
	'''Manually refresh the cached leaderboards (e.g. to seed them at deploy
	time, before the daily cron job first runs).'''
	leaderboard_recalc(db_session(), cache)
