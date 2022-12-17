import time

from sqlalchemy.sql import func

from files.helpers.const import *


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


def sort_objects(objects, sort, cls):
	if sort == 'hot':
		ti = int(time.time()) + 3600
		return objects.order_by(
			-100000
				* (cls.upvotes + 1)
				/ (func.power((ti - cls.created_utc) / 1000, 1.23)),
			cls.created_utc.desc())
	elif sort == 'bump' and cls.__name__ == 'Submission':
		return objects.filter(cls.comment_count > 1).order_by(
			cls.bump_utc.desc(), cls.created_utc.desc())
	elif sort == 'comments' and cls.__name__ == 'Submission':
		return objects.order_by(
			cls.comment_count.desc(), cls.created_utc.desc())
	elif sort == 'controversial':
		return objects.order_by(
			(cls.upvotes + 1) / (cls.downvotes + 1)
				+ (cls.downvotes + 1) / (cls.upvotes + 1),
			cls.downvotes.desc(), cls.created_utc.desc())
	elif sort == 'top':
		return objects.order_by(
			cls.downvotes - cls.upvotes, cls.created_utc.desc())
	elif sort == 'bottom':
		return objects.order_by(
			cls.upvotes - cls.downvotes, cls.created_utc.desc())
	elif sort == 'old':
		return objects.order_by(cls.created_utc)
	else: # default, or sort == 'new'
		return objects.order_by(cls.created_utc.desc())


# Presently designed around files.helpers.get.get_comment_trees_eager
# Behavior should parallel that of sort_objects above. TODO: Unify someday?
def sort_comment_results(comments, sort):
	DESC = (2 << 30) - 1 # descending sorts, Y2038 problem, change before then
	if sort == 'hot':
		ti = int(time.time()) + 3600
		key_func = lambda c: (
			-100000
				* (c.upvotes + 1)
				/ (pow(((ti - c.created_utc) / 1000), 1.23)),
			DESC - c.created_utc
		)
	elif sort == 'controversial':
		key_func = lambda c: (
			(c.upvotes + 1) / (c.downvotes + 1)
				+ (c.downvotes + 1) / (c.upvotes + 1),
			DESC - c.downvotes,
			DESC - c.created_utc
		)
	elif sort == 'top':
		key_func = lambda c: (c.downvotes - c.upvotes, DESC - c.created_utc)
	elif sort == 'bottom':
		key_func = lambda c: (c.upvotes - c.downvotes, DESC - c.created_utc)
	elif sort == 'old':
		key_func = lambda c: c.created_utc
	else: # default, or sort == 'new'
		key_func = lambda c: DESC - c.created_utc

	key_func_pinned = lambda c: (
		(c.is_pinned is None, c.is_pinned == '', c.is_pinned), # sort None last
		key_func(c))
	return sorted(comments, key=key_func_pinned)
