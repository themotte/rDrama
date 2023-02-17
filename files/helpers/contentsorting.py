import time
from collections.abc import Iterable
from typing import Union

from sqlalchemy.sql import func
from sqlalchemy.orm import Query

from files.classes.comment import Comment
from files.classes.submission import Submission
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


def sort_objects(objects: Query, sort: str, cls: type[Union[Comment, Submission]]):
	if sort == 'hot':
		ti = int(time.time()) + 3600
		ordered = objects.order_by(
			-100000
				* (cls.upvotes + 1)
				/ (func.power((ti - cls.created_utc) / 1000, 1.23)))
	elif sort == 'bump' and cls is Submission:
		ordered = objects.filter(cls.comment_count > 1).order_by(cls.bump_utc.desc())
	elif sort == 'comments':
		if cls is Submission:
			ordered = objects.order_by(cls.comment_count.desc())
		elif cls is Comment:
			ordered = objects.order_by(cls.descendant_count.desc())
		else:
			ordered = objects
	elif sort == 'controversial':
		ordered = objects.order_by(
			(cls.upvotes + 1) / (cls.downvotes + 1)
				+ (cls.downvotes + 1) / (cls.upvotes + 1),
			cls.downvotes.desc())
	elif sort == 'top':
		ordered = objects.order_by(cls.downvotes - cls.upvotes)
	elif sort == 'bottom':
		ordered = objects.order_by(cls.upvotes - cls.downvotes)
	elif sort == 'old':
		return objects.order_by(cls.created_utc)
	else:
		ordered = objects
	ordered = ordered.order_by(cls.created_utc.desc())
	return ordered


# Presently designed around files.helpers.get.get_comment_trees_eager
# Behavior should parallel that of sort_objects above. TODO: Unify someday?
def sort_comment_results(comments: Iterable[Comment], sort:str):
	if sort == 'hot':
		ti = int(time.time()) + 3600
		key_func = lambda c: (
			-100000
				* (c.upvotes + 1)
				/ (pow(((ti - c.created_utc) / 1000), 1.23)),
			-c.created_utc
		)
	elif sort == 'comments':
		key_func = lambda c: -c.descendant_count
	elif sort == 'controversial':
		key_func = lambda c: (
			(c.upvotes + 1) / (c.downvotes + 1)
				+ (c.downvotes + 1) / (c.upvotes + 1),
			-c.downvotes,
			-c.created_utc
		)
	elif sort == 'top':
		key_func = lambda c: (c.downvotes - c.upvotes, -c.created_utc)
	elif sort == 'bottom':
		key_func = lambda c: (c.upvotes - c.downvotes, -c.created_utc)
	elif sort == 'old':
		key_func = lambda c: c.created_utc
	else: # default, or sort == 'new'
		key_func = lambda c: -c.created_utc

	key_func_pinned = lambda c: (
		(c.is_pinned is None, c.is_pinned == '', c.is_pinned), # sort None last
		key_func(c))
	return sorted(comments, key=key_func_pinned)
