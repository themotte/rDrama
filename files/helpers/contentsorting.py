import time

from sqlalchemy.sql import case, cast, func
from sqlalchemy.sql.sqltypes import Numeric
from sqlalchemy.orm import Query

from files.helpers.config.const import *


def apply_time_filter(objects, t, cls):
	now = int(time.time())
	if t == 'hour':
		cutoff = now - (60 * 60)
	elif t == 'day':
		cutoff = now - (24 * 60 * 60)
	elif t == 'week':
		cutoff = now - (7 * 24 * 60 * 60)
	elif t == 'month':
		cutoff = now - (30 * 24 * 60 * 60)
	elif t == 'year':
		cutoff = now - (365 * 24 * 60 * 60)
	else:
		cutoff = 0
	return objects.filter(cls.created_utc >= cutoff)


def pinned_comments_first(cls) -> tuple:
	'''For comments (`cls` being the comment class, passed for the import cycle): the order keys putting pinned ones first, newest first among themselves.'''
	pinned = cls.is_pinned != None
	return (pinned.desc(), case((pinned, cls.created_utc)).desc().nulls_last(), case((pinned, cls.id)).desc().nulls_last())


def sort_objects(objects: Query, sort: str, cls):
	if sort == 'hot':
		ti = int(time.time()) + 3600
		ordered = objects.order_by(
			-100000
				* (cast(cls.upvotes, Numeric) + 1)
				# An age under a second, for posts dated an hour or more ahead, counts as a second
				/ (func.power(func.greatest(ti - cls.created_utc, 1) / 1000, 1.23)))
	elif sort == 'comments':
		if cls.__name__ == 'Submission': # we're checking the stringified name due to a gnarly import cycle
			ordered = objects.order_by(cls.comment_count.desc())
		else:
			ordered = objects.order_by(cls.descendant_count.desc())
	elif sort == 'controversial':
		ordered = objects.order_by(
			(cast(cls.upvotes, Numeric) + 1) / (cast(cls.downvotes, Numeric) + 1)
				+ (cast(cls.downvotes, Numeric) + 1) / (cast(cls.upvotes, Numeric) + 1),
			cls.downvotes.desc())
	elif sort == 'top':
		ordered = objects.order_by(cls.downvotes - cls.upvotes)
	elif sort == 'bottom':
		ordered = objects.order_by(cls.upvotes - cls.downvotes)
	elif sort == 'old':
		return objects.order_by(cls.created_utc, cls.id)
	else: # default, or sort == 'new'
		ordered = objects
	# Ties go newest first, and the id makes the order total, so pages neither repeat nor skip rows
	ordered = ordered.order_by(cls.created_utc.desc(), cls.id.desc())
	return ordered


def sort_comments(objects: Query, sort: str, cls) -> Query:
	'''Orders comments (`cls` being the comment class, passed for the import cycle) as a post page shows them: pinned ones first, newest first among themselves, then by `sort`.'''
	return sort_objects(objects.order_by(*pinned_comments_first(cls)), sort, cls)
